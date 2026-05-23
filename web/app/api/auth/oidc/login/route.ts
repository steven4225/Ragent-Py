import { NextResponse } from "next/server";

import { buildOidcAuthorizationUrl, generateOidcState, resolveOidcConfig } from "@/lib/auth/oidc";
import { isOidcEnabled, setOidcStateCookie } from "@/lib/auth/session";

function resolveRedirectUri(request: Request): string {
  const configured = process.env.AUTH_OIDC_REDIRECT_URI?.trim();
  if (configured) return configured;
  const origin = new URL(request.url).origin;
  return `${origin}/api/auth/oidc/callback`;
}

export async function GET(request: Request) {
  if (!isOidcEnabled()) {
    return NextResponse.json(
      {
        code: "OIDC_DISABLED",
        message: "OIDC auth provider is disabled."
      },
      { status: 404 }
    );
  }

  try {
    const config = await resolveOidcConfig();
    const redirectUri = resolveRedirectUri(request);
    const state = generateOidcState();
    const redirectUrl = buildOidcAuthorizationUrl({
      config,
      state,
      redirectUri
    });

    const response = NextResponse.redirect(redirectUrl);
    setOidcStateCookie(response, state);
    return response;
  } catch (error) {
    const message = error instanceof Error ? error.message : "OIDC login could not be initialized.";
    return NextResponse.json(
      {
        code: "OIDC_CONFIG_INVALID",
        message
      },
      { status: 500 }
    );
  }
}
