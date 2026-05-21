import { NextResponse } from "next/server";

import { streamAssistantText } from "@/lib/ai/generation-adapter";
import { requireSignedInApi, requireTenantScopeApi, toAuthErrorResponse } from "@/lib/auth/session";
import { conversationRepository, messageRepository, traceRepository } from "@/lib/repositories/platform-repositories";
import { appendPythonTraceStages, isPythonBackendEnabled, postPythonJson, type PythonInternalChatPayload } from "@/lib/server/python-backend";
import { prepareChatTurn } from "@/lib/server/chat-turn";
import { createTraceId, createTraceRunId } from "@/lib/trace/trace";

type StreamEvent =
  | {
      type: "chat.started";
      traceId: string;
      conversation: unknown;
      userMessage: unknown;
    }
  | {
      type: "tool.call";
      traceId: string;
      toolCall: unknown;
    }
  | {
      type: "message.delta";
      traceId: string;
      delta: string;
    }
  | {
      type: "message.completed";
      traceId: string;
      assistantMessage: unknown;
    }
  | {
      type: "chat.completed";
      traceId: string;
      plan: unknown;
      traceStages?: unknown;
    }
  | {
      type: "thinking.delta";
      traceId: string;
      delta: string;
    }
  | {
      type: "thinking.completed";
      traceId: string;
    }
  | {
      type: "chat.error";
      traceId: string;
      code: string;
      message: string;
    };

function toNdjson(event: StreamEvent) {
  return `${JSON.stringify(event)}\n`;
}

export async function POST(request: Request) {
  let conversationId: string | null = null;

  try {
    const user = requireTenantScopeApi(requireSignedInApi(request));
    const body = (await request.json().catch(() => ({}))) as { message?: string; conversationId?: string };
    const rawMessage = body.message?.trim();
    const traceId = createTraceId("chat");
    const runId = createTraceRunId(traceId);
    const runStartedAt = new Date().toISOString();

    if (!rawMessage) {
      return NextResponse.json(
        {
          code: "BAD_REQUEST",
          message: "`message` is required.",
          traceId
        },
        { status: 400 }
      );
    }

    const conversation = body.conversationId
      ? conversationRepository.getByIdForUser(body.conversationId, user.userId, { tenantId: user.tenantId, orgId: user.orgId ?? null })
      : conversationRepository.create({
          title: "Untitled conversation",
          userId: user.userId,
          tenantId: user.tenantId,
          orgId: user.orgId ?? null
        });
    if (!conversation) {
      return NextResponse.json(
        {
          code: "NOT_FOUND",
          message: "Conversation does not exist.",
          traceId
        },
        { status: 404 }
      );
    }

    conversationId = conversation.conversationId;
    if (isPythonBackendEnabled()) {
      const userMessage = messageRepository.append({
        conversationId: conversation.conversationId,
        role: "user",
        content: rawMessage,
        metadata: {
          tenantId: user.tenantId,
          orgId: user.orgId ?? null,
          userId: user.userId,
          backend: "python"
        }
      });
      const pythonPayload: PythonInternalChatPayload = {
        message: rawMessage,
        conversationId: conversation.conversationId,
        userId: user.userId,
        tenantId: user.tenantId,
        orgId: user.orgId ?? null,
        role: user.role
      };
      const pythonResponse = await postPythonJson("/internal/chat/stream", pythonPayload);
      if (!pythonResponse.ok || !pythonResponse.body) {
        const pythonBody = await pythonResponse.json().catch(() => null);
        const code =
          pythonBody && typeof pythonBody === "object" && "code" in pythonBody && typeof pythonBody.code === "string"
            ? pythonBody.code
            : "PYTHON_BACKEND_ERROR";
        const message =
          pythonBody && typeof pythonBody === "object" && "message" in pythonBody && typeof pythonBody.message === "string"
            ? pythonBody.message
            : "Python backend chat stream request failed.";
        const failedTraceId =
          pythonBody && typeof pythonBody === "object" && "traceId" in pythonBody && typeof pythonBody.traceId === "string"
            ? pythonBody.traceId
            : traceId;
        return NextResponse.json(
          {
            code,
            message,
            traceId: failedTraceId
          },
          { status: pythonResponse.status || 502 }
        );
      }

      const decoder = new TextDecoder();
      const encoder = new TextEncoder();
      const pythonReader = pythonResponse.body.getReader();
      let streamTraceId = traceId;

      const stream = new ReadableStream<Uint8Array>({
        async start(controller) {
          let buffer = "";
          const emitEvent = (event: StreamEvent) => {
            controller.enqueue(encoder.encode(toNdjson(event)));
          };
          const processEvent = (event: StreamEvent): StreamEvent => {
            if (typeof event.traceId === "string") {
              streamTraceId = event.traceId;
            }
            if (event.type === "chat.started") {
              return {
                type: "chat.started",
                traceId: streamTraceId,
                conversation,
                userMessage
              };
            }
            if (event.type === "message.completed") {
              const assistantPayload =
                event.assistantMessage && typeof event.assistantMessage === "object"
                  ? event.assistantMessage as { content?: unknown; metadata?: unknown }
                  : null;
              const assistantMessage = messageRepository.append({
                conversationId: conversation.conversationId,
                role: "assistant",
                content: typeof assistantPayload?.content === "string" ? assistantPayload.content : "",
                metadata: {
                  traceId: streamTraceId,
                  source: "python-backend",
                  tenantId: user.tenantId,
                  orgId: user.orgId ?? null,
                  userId: user.userId,
                  ...(assistantPayload?.metadata && typeof assistantPayload.metadata === "object"
                    ? assistantPayload.metadata as Record<string, unknown>
                    : {})
                }
              });
              return {
                type: "message.completed",
                traceId: streamTraceId,
                assistantMessage
              };
            }
            if (event.type === "chat.completed") {
              const planPayload =
                event.plan && typeof event.plan === "object"
                  ? event.plan as { useRetrieval?: unknown; useTools?: unknown; retrievalReason?: unknown }
                  : null;
              appendPythonTraceStages({
                traceId: streamTraceId,
                conversationId: conversation.conversationId,
                traceStages: event.traceStages,
                scope: {
                  tenantId: user.tenantId,
                  orgId: user.orgId ?? null,
                  userId: user.userId,
                  role: user.role,
                },
              });
              traceRepository.append({
                traceId: streamTraceId,
                runId: createTraceRunId(streamTraceId),
                nodeId: `node:${streamTraceId}:chat:root`,
                conversationId: conversation.conversationId,
                stage: "chat",
                status: "succeeded",
                startedAt: runStartedAt,
                finishedAt: new Date().toISOString(),
                metadata: {
                  backend: "python",
                  useRetrieval: planPayload?.useRetrieval === true,
                  useTools: planPayload?.useTools === true
                },
                scope: {
                  tenantId: user.tenantId,
                  orgId: user.orgId ?? null,
                  userId: user.userId,
                  role: user.role
                }
              });
              return {
                type: "chat.completed",
                traceId: streamTraceId,
                plan: {
                  useRetrieval: planPayload?.useRetrieval === true,
                  useTools: planPayload?.useTools === true,
                  retrievalReason:
                    typeof planPayload?.retrievalReason === "string"
                      ? planPayload.retrievalReason
                      : "Python backend phase-1 chat path."
                }
              };
            }
            if (event.type === "chat.error") {
              traceRepository.append({
                traceId: streamTraceId,
                runId: createTraceRunId(streamTraceId),
                nodeId: `node:${streamTraceId}:chat:root`,
                conversationId: conversation.conversationId,
                stage: "chat",
                status: "failed",
                startedAt: runStartedAt,
                finishedAt: new Date().toISOString(),
                metadata: {
                  backend: "python",
                  code: event.code,
                  error: event.message
                },
                scope: {
                  tenantId: user.tenantId,
                  orgId: user.orgId ?? null,
                  userId: user.userId,
                  role: user.role
                }
              });
            }
            return event;
          };

          try {
            while (true) {
              const { done, value } = await pythonReader.read();
              if (done) break;
              buffer += decoder.decode(value, { stream: true });
              const lines = buffer.split("\n");
              buffer = lines.pop() ?? "";
              for (const line of lines) {
                if (!line.trim()) continue;
                emitEvent(processEvent(JSON.parse(line) as StreamEvent));
              }
            }

            if (buffer.trim()) {
              emitEvent(processEvent(JSON.parse(buffer) as StreamEvent));
            }
            controller.close();
          } catch (error) {
            emitEvent({
              type: "chat.error",
              traceId: streamTraceId,
              code: "PYTHON_STREAM_PROXY_FAILED",
              message: error instanceof Error ? error.message : "Python stream proxy failed."
            });
            controller.close();
          } finally {
            try { pythonReader.releaseLock(); } catch { /* no-op */ }
          }
        }
      });

      return new Response(stream, {
        headers: {
          "Content-Type": "application/x-ndjson",
          "Cache-Control": "no-cache, no-transform",
          Connection: "keep-alive"
        }
      });
    }

    const toolCallUpdates: Array<{
      toolCallId: string;
      toolName: string;
      status: "queued" | "running" | "succeeded" | "failed";
      args: Record<string, unknown>;
      output?: unknown;
    }> = [];
    const prepared = await prepareChatTurn({
      conversationId: conversation.conversationId,
      userId: conversation.userId,
      userRole: user.role,
      tenantId: user.tenantId,
      orgId: user.orgId ?? null,
      message: rawMessage,
      traceId,
      onToolCallUpdate: (update) => {
        toolCallUpdates.push(update);
      }
    });

    const userMessage = messageRepository.append({
      conversationId: conversation.conversationId,
      role: "user",
      content: rawMessage,
      metadata: {
        tenantId: user.tenantId,
        orgId: user.orgId ?? null,
        userId: user.userId
      }
    });

    const generation = streamAssistantText({
      messages: prepared.messages
    });

    const stream = new ReadableStream<Uint8Array>({
      async start(controller) {
        const encoder = new TextEncoder();
        let assistantText = "";

        try {
          controller.enqueue(
            encoder.encode(
              toNdjson({
                type: "chat.started",
                traceId,
                conversation,
                userMessage
              })
            )
          );

          for (const toolCall of toolCallUpdates) {
            controller.enqueue(
              encoder.encode(
                toNdjson({
                  type: "tool.call",
                  traceId,
                  toolCall
                })
              )
            );
          }

          for await (const chunk of generation.result.textStream) {
            assistantText += chunk;
            controller.enqueue(
              encoder.encode(
                toNdjson({
                  type: "message.delta",
                  traceId,
                  delta: chunk
                })
              )
            );
          }

          const assistantMessage = messageRepository.append({
            conversationId: conversation.conversationId,
            role: "assistant",
            content: assistantText.trim(),
            metadata: {
              traceId,
              source: "ts-ai-sdk",
              toolCalls: prepared.toolCalls,
              retrievalBoundary: prepared.retrievalBoundary,
              generation: {
                provider: "ai-sdk",
                mode: "streamText",
                model: generation.model
              },
              tenantId: user.tenantId,
              orgId: user.orgId ?? null,
              userId: user.userId,
              ...prepared.metadata
            }
          });

          for (const stage of prepared.traceStages) {
            traceRepository.append({
              traceId,
              runId,
              conversationId: conversation.conversationId,
              stage: stage.stage,
              status: stage.status,
              metadata: {
                ...stage.metadata,
                tenantId: user.tenantId,
                orgId: user.orgId ?? null,
                userId: user.userId,
                role: user.role
              },
              scope: {
                tenantId: user.tenantId,
                orgId: user.orgId ?? null,
                userId: user.userId,
                role: user.role
              }
            });
          }

          traceRepository.append({
            traceId,
            runId,
            conversationId: conversation.conversationId,
            stage: "generation.completed",
            status: "succeeded",
            metadata: {
              provider: "ai-sdk",
              mode: "streamText",
              model: generation.model,
              outputLength: assistantText.trim().length
            },
            scope: {
              tenantId: user.tenantId,
              orgId: user.orgId ?? null,
              userId: user.userId,
              role: user.role
            }
          });

          traceRepository.append({
            traceId,
            runId,
            nodeId: `node:${traceId}:chat:root`,
            conversationId: conversation.conversationId,
            stage: "chat",
            status: "succeeded",
            startedAt: runStartedAt,
            finishedAt: new Date().toISOString(),
            metadata: {
              useRetrieval: prepared.plan.useRetrieval,
              useTools: prepared.plan.useTools
            },
            scope: {
              tenantId: user.tenantId,
              orgId: user.orgId ?? null,
              userId: user.userId,
              role: user.role
            }
          });

          controller.enqueue(
            encoder.encode(
              toNdjson({
                type: "message.completed",
                traceId,
                assistantMessage
              })
            )
          );

          controller.enqueue(
            encoder.encode(
              toNdjson({
                type: "chat.completed",
                traceId,
                plan: prepared.plan
              })
            )
          );
        } catch (error) {
          const message = error instanceof Error ? error.message : "Unknown stream error";
          traceRepository.append({
            traceId,
            runId,
            conversationId: conversation.conversationId,
            stage: "generation.failed",
            status: "failed",
            metadata: {
              provider: "ai-sdk",
              mode: "streamText",
              model: generation.model,
              error: message
            },
            scope: {
              tenantId: user.tenantId,
              orgId: user.orgId ?? null,
              userId: user.userId,
              role: user.role
            }
          });
          traceRepository.append({
            traceId,
            runId,
            nodeId: `node:${traceId}:chat:root`,
            conversationId: conversation.conversationId,
            stage: "chat",
            status: "failed",
            startedAt: runStartedAt,
            finishedAt: new Date().toISOString(),
            metadata: {
              useRetrieval: prepared.plan.useRetrieval,
              useTools: prepared.plan.useTools,
              error: message
            },
            scope: {
              tenantId: user.tenantId,
              orgId: user.orgId ?? null,
              userId: user.userId,
              role: user.role
            }
          });
          controller.enqueue(
            encoder.encode(
              toNdjson({
                type: "chat.error",
                traceId,
                code: "STREAM_ERROR",
                message
              })
            )
          );
        } finally {
          controller.close();
        }
      }
    });

    return new Response(stream, {
      headers: {
        "Content-Type": "application/x-ndjson; charset=utf-8",
        "Cache-Control": "no-cache, no-transform",
        Connection: "keep-alive"
      }
    });
  } catch (error) {
    const authResponse = toAuthErrorResponse(error);
    if (authResponse) return authResponse;
    return NextResponse.json(
      {
        code: "STREAM_PREPARATION_FAILED",
        message: error instanceof Error ? error.message : "Stream preparation failed.",
        conversationId
      },
      { status: 500 }
    );
  }
}
