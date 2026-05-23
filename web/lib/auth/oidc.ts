import { randomBytes } from "node:crypto";

import { userRepository } from "@/lib/repositories/platform-repositories";

import type { SessionRole, SessionUser } from "@/lib/auth/session";

export type OidcConfig = {
  authorizationEndpoint: string;
  tokenEndpoint: string;
  userInfoEndpoint: string;
  endSessionEndpoint: string | null;
  clientId: string;
  clientSecret: string;
  scope: string;
  userIdClaim: string;
  nameClaim: string;
  roleClaim: string;
  tenantClaim: string;
  orgClaim: string;
  adminRoleValues: string[];
  defaultRole: SessionRole;
  defaultTenantId: string | null;
  defaultOrgId: string | null;
  // Source for diagnostics: "explicit" when all three endpoints were
  // pulled from env vars, "discovery" when at least one was filled in
  // from the issuer's /.well-known/openid-configuration document.
  source: "explicit" | "discovery";
};

type DiscoveryDocument = {
  authorization_endpoint?: unknown;
  token_endpoint?: unknown;
  userinfo_endpoint?: unknown;
  end_session_endpoint?: unknown;
};

const discoveryCache = new Map<string, DiscoveryDocument>();

export function __resetOidcDiscoveryCacheForTests(): void {
  discoveryCache.clear();
}

async function fetchDiscoveryDocument(issuer: string): Promise<DiscoveryDocument> {
  // Cache per-process; OIDC discovery documents are intentionally
  // long-lived and only change when the IdP is reconfigured. A cold
  // restart will refetch.
  const cached = discoveryCache.get(issuer);
  if (cached) return cached;

  const url = issuer.endsWith("/") ? `${issuer}.well-known/openid-configuration` : `${issuer}/.well-known/openid-configuration`;
  const response = await fetch(url, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store"
  });
  if (!response.ok) {
    throw new Error(`OIDC discovery failed at ${url}: status ${response.status}.`);
  }
  const payload = (await response.json().catch(() => ({}))) as DiscoveryDocument;
  discoveryCache.set(issuer, payload);
  return payload;
}

function normalizeString(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const normalized = value.trim();
  return normalized.length > 0 ? normalized : null;
}

function normalizeRole(value: string | null): SessionRole | null {
  if (!value) return null;
  const normalized = value.toLowerCase();
  if (normalized === "admin" || normalized === "user") return normalized;
  return null;
}

function splitCsv(value: string | undefined, fallback: string[]): string[] {
  const normalized =
    value
      ?.split(",")
      .map((item) => item.trim().toLowerCase())
      .filter(Boolean) ?? [];
  return normalized.length > 0 ? normalized : fallback;
}

function claimToString(value: unknown): string | null {
  if (typeof value === "string") return normalizeString(value);
  if (Array.isArray(value)) {
    for (const item of value) {
      const normalized = claimToString(item);
      if (normalized) return normalized;
    }
  }
  return null;
}

function claimToStrings(value: unknown): string[] {
  if (typeof value === "string") {
    return value
      .split(/[,\s]+/)
      .map((item) => item.trim().toLowerCase())
      .filter(Boolean);
  }
  if (Array.isArray(value)) {
    return value
      .flatMap((item) => claimToStrings(item))
      .map((item) => item.toLowerCase())
      .filter(Boolean);
  }
  return [];
}

function encodeBase64Url(bytes: Uint8Array): string {
  return Buffer.from(bytes).toString("base64url");
}

export function generateOidcState(): string {
  return encodeBase64Url(randomBytes(24));
}

function buildClaimsConfig(): Omit<OidcConfig, "authorizationEndpoint" | "tokenEndpoint" | "userInfoEndpoint" | "endSessionEndpoint" | "clientId" | "clientSecret" | "source"> {
  return {
    scope: normalizeString(process.env.AUTH_OIDC_SCOPES) ?? "openid profile email",
    userIdClaim: normalizeString(process.env.AUTH_OIDC_USER_ID_CLAIM) ?? "sub",
    nameClaim: normalizeString(process.env.AUTH_OIDC_NAME_CLAIM) ?? "name",
    roleClaim: normalizeString(process.env.AUTH_OIDC_ROLE_CLAIM) ?? "role",
    tenantClaim: normalizeString(process.env.AUTH_OIDC_TENANT_CLAIM) ?? "tenant_id",
    orgClaim: normalizeString(process.env.AUTH_OIDC_ORG_CLAIM) ?? "org_id",
    adminRoleValues: splitCsv(process.env.AUTH_OIDC_ADMIN_ROLE_VALUES, ["admin"]),
    defaultRole: normalizeRole(normalizeString(process.env.AUTH_OIDC_DEFAULT_ROLE)) ?? "user",
    defaultTenantId: normalizeString(process.env.AUTH_OIDC_DEFAULT_TENANT_ID),
    defaultOrgId: normalizeString(process.env.AUTH_OIDC_DEFAULT_ORG_ID)
  };
}

export function getOidcConfig(): OidcConfig {
  // Synchronous path. Requires every endpoint to be pinned as an env
  // var; if you only have AUTH_OIDC_ISSUER, call resolveOidcConfig()
  // instead — that one will discover the endpoints from
  // /.well-known/openid-configuration.
  const authorizationEndpoint = normalizeString(process.env.AUTH_OIDC_AUTHORIZATION_ENDPOINT);
  const tokenEndpoint = normalizeString(process.env.AUTH_OIDC_TOKEN_ENDPOINT);
  const userInfoEndpoint = normalizeString(process.env.AUTH_OIDC_USERINFO_ENDPOINT);
  const endSessionEndpoint = normalizeString(process.env.AUTH_OIDC_END_SESSION_ENDPOINT);
  const clientId = normalizeString(process.env.AUTH_OIDC_CLIENT_ID);
  const clientSecret = normalizeString(process.env.AUTH_OIDC_CLIENT_SECRET);

  if (!authorizationEndpoint || !tokenEndpoint || !userInfoEndpoint || !clientId || !clientSecret) {
    throw new Error(
      "OIDC is enabled but required env vars are missing. Either set AUTH_OIDC_ISSUER (recommended) and call resolveOidcConfig(), or set all of AUTH_OIDC_AUTHORIZATION_ENDPOINT, AUTH_OIDC_TOKEN_ENDPOINT, AUTH_OIDC_USERINFO_ENDPOINT, AUTH_OIDC_CLIENT_ID, AUTH_OIDC_CLIENT_SECRET."
    );
  }

  return {
    authorizationEndpoint,
    tokenEndpoint,
    userInfoEndpoint,
    endSessionEndpoint,
    clientId,
    clientSecret,
    source: "explicit",
    ...buildClaimsConfig()
  };
}

export async function resolveOidcConfig(): Promise<OidcConfig> {
  // Preferred entry point: pulls anything missing from
  // /.well-known/openid-configuration when AUTH_OIDC_ISSUER is set.
  // If every endpoint env var is already pinned, this is equivalent
  // to getOidcConfig() and never touches the network.
  const clientId = normalizeString(process.env.AUTH_OIDC_CLIENT_ID);
  const clientSecret = normalizeString(process.env.AUTH_OIDC_CLIENT_SECRET);
  if (!clientId || !clientSecret) {
    throw new Error("OIDC is enabled but AUTH_OIDC_CLIENT_ID / AUTH_OIDC_CLIENT_SECRET are not set.");
  }

  const explicitAuth = normalizeString(process.env.AUTH_OIDC_AUTHORIZATION_ENDPOINT);
  const explicitToken = normalizeString(process.env.AUTH_OIDC_TOKEN_ENDPOINT);
  const explicitUserInfo = normalizeString(process.env.AUTH_OIDC_USERINFO_ENDPOINT);
  const explicitEndSession = normalizeString(process.env.AUTH_OIDC_END_SESSION_ENDPOINT);
  const issuer = normalizeString(process.env.AUTH_OIDC_ISSUER);

  let authorizationEndpoint = explicitAuth;
  let tokenEndpoint = explicitToken;
  let userInfoEndpoint = explicitUserInfo;
  let endSessionEndpoint = explicitEndSession;
  let source: "explicit" | "discovery" = "explicit";

  const needsDiscovery = !authorizationEndpoint || !tokenEndpoint || !userInfoEndpoint;
  if (needsDiscovery) {
    if (!issuer) {
      throw new Error(
        "OIDC discovery cannot proceed: set AUTH_OIDC_ISSUER, or provide all three endpoint env vars explicitly (AUTH_OIDC_AUTHORIZATION_ENDPOINT, AUTH_OIDC_TOKEN_ENDPOINT, AUTH_OIDC_USERINFO_ENDPOINT)."
      );
    }
    const document = await fetchDiscoveryDocument(issuer);
    authorizationEndpoint = authorizationEndpoint ?? claimToString(document.authorization_endpoint);
    tokenEndpoint = tokenEndpoint ?? claimToString(document.token_endpoint);
    userInfoEndpoint = userInfoEndpoint ?? claimToString(document.userinfo_endpoint);
    endSessionEndpoint = endSessionEndpoint ?? claimToString(document.end_session_endpoint);
    source = "discovery";
  }

  if (!authorizationEndpoint || !tokenEndpoint || !userInfoEndpoint) {
    throw new Error(
      "OIDC discovery completed but the issuer document is missing required endpoints (authorization_endpoint / token_endpoint / userinfo_endpoint)."
    );
  }

  return {
    authorizationEndpoint,
    tokenEndpoint,
    userInfoEndpoint,
    endSessionEndpoint,
    clientId,
    clientSecret,
    source,
    ...buildClaimsConfig()
  };
}

export function buildOidcAuthorizationUrl(params: {
  config: OidcConfig;
  state: string;
  redirectUri: string;
}): string {
  const url = new URL(params.config.authorizationEndpoint);
  url.searchParams.set("response_type", "code");
  url.searchParams.set("client_id", params.config.clientId);
  url.searchParams.set("redirect_uri", params.redirectUri);
  url.searchParams.set("scope", params.config.scope);
  url.searchParams.set("state", params.state);
  return url.toString();
}

export async function exchangeOidcCode(params: {
  config: OidcConfig;
  code: string;
  redirectUri: string;
}): Promise<{ accessToken: string }> {
  const body = new URLSearchParams({
    grant_type: "authorization_code",
    code: params.code,
    redirect_uri: params.redirectUri,
    client_id: params.config.clientId,
    client_secret: params.config.clientSecret
  });

  const response = await fetch(params.config.tokenEndpoint, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
      Accept: "application/json"
    },
    body: body.toString(),
    cache: "no-store"
  });

  const payload = (await response.json().catch(() => ({}))) as Record<string, unknown>;
  const accessToken = normalizeString(payload.access_token);

  if (!response.ok || !accessToken) {
    throw new Error(`OIDC token exchange failed with status ${response.status}.`);
  }

  return { accessToken };
}

export async function fetchOidcUserInfo(params: { config: OidcConfig; accessToken: string }): Promise<Record<string, unknown>> {
  const response = await fetch(params.config.userInfoEndpoint, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${params.accessToken}`,
      Accept: "application/json"
    },
    cache: "no-store"
  });
  const payload = (await response.json().catch(() => ({}))) as Record<string, unknown>;
  if (!response.ok) {
    throw new Error(`OIDC userinfo failed with status ${response.status}.`);
  }
  return payload;
}

export function mapOidcClaimsToSessionUser(claims: Record<string, unknown>, config: OidcConfig): SessionUser {
  const repoByUserId = (userId: string) => userRepository.getByUserId(userId);

  const userId =
    claimToString(claims[config.userIdClaim]) ??
    claimToString(claims.sub) ??
    claimToString(claims.email) ??
    claimToString(claims.preferred_username);

  if (!userId) {
    throw new Error("OIDC identity cannot be mapped to SessionUser.userId (missing subject/email claim).");
  }

  const stored = repoByUserId(userId);
  const roleCandidates = claimToStrings(claims[config.roleClaim]);
  const roleFromClaim = roleCandidates.some((item) => config.adminRoleValues.includes(item))
    ? "admin"
    : normalizeRole(claimToString(claims[config.roleClaim]));
  const role = roleFromClaim ?? stored?.role ?? config.defaultRole;

  const tenantId = claimToString(claims[config.tenantClaim]) ?? stored?.tenantId ?? config.defaultTenantId ?? null;
  const orgId = claimToString(claims[config.orgClaim]) ?? stored?.orgId ?? config.defaultOrgId ?? null;
  const name =
    claimToString(claims[config.nameClaim]) ??
    claimToString(claims.name) ??
    claimToString(claims.preferred_username) ??
    claimToString(claims.email) ??
    stored?.name ??
    userId;

  return {
    id: userId,
    userId,
    role,
    name,
    tenantId,
    orgId
  };
}
