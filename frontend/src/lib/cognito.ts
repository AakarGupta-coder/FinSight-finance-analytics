// Minimal Amazon Cognito User Pools client using the public (unauthenticated)
// IdP API over HTTPS. Used only when the backend reports auth_mode = "cognito".
// The app client must have no secret and allow USER_PASSWORD_AUTH.

export interface CognitoConfig { user_pool_id: string; client_id: string; region: string }

export interface CognitoTokens { accessToken: string; idToken: string; refreshToken?: string; expiresIn: number }

export class CognitoError extends Error {
  code: string
  constructor(code: string, message: string) {
    super(message)
    this.code = code
  }
}

const FRIENDLY: Record<string, string> = {
  NotAuthorizedException: 'Incorrect email or password.',
  UserNotFoundException: 'Incorrect email or password.',
  UsernameExistsException: 'An account with this email already exists.',
  UserNotConfirmedException: 'Please confirm your email address before signing in.',
  CodeMismatchException: 'The confirmation code is incorrect.',
  ExpiredCodeException: 'The confirmation code has expired. Request a new one.',
  InvalidPasswordException: 'Password does not meet the requirements.',
  TooManyRequestsException: 'Too many attempts. Please wait and try again.',
  LimitExceededException: 'Too many attempts. Please wait and try again.',
}

async function call<T>(config: CognitoConfig, action: string, body: Record<string, unknown>): Promise<T> {
  let res: Response
  try {
    res = await fetch(`https://cognito-idp.${config.region}.amazonaws.com/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-amz-json-1.1',
        'X-Amz-Target': `AWSCognitoIdentityProviderService.${action}`,
      },
      body: JSON.stringify(body),
    })
  } catch {
    throw new CognitoError('network_error', 'Cannot reach the sign-in service.')
  }
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    const code = String(data.__type ?? 'Unknown').split('#').pop() ?? 'Unknown'
    throw new CognitoError(code, FRIENDLY[code] ?? data.message ?? 'Sign-in failed.')
  }
  return data as T
}

interface AuthResult { AuthenticationResult?: { AccessToken: string; IdToken: string; RefreshToken?: string; ExpiresIn: number }; ChallengeName?: string }

function tokens(result: AuthResult, refreshToken?: string): CognitoTokens {
  const r = result.AuthenticationResult
  if (!r) throw new CognitoError(result.ChallengeName ?? 'Challenge', 'Additional sign-in steps are required, which this app does not support yet.')
  return { accessToken: r.AccessToken, idToken: r.IdToken, refreshToken: r.RefreshToken ?? refreshToken, expiresIn: r.ExpiresIn }
}

export const cognito = {
  async signIn(config: CognitoConfig, email: string, password: string) {
    const result = await call<AuthResult>(config, 'InitiateAuth', {
      AuthFlow: 'USER_PASSWORD_AUTH', ClientId: config.client_id, AuthParameters: { USERNAME: email, PASSWORD: password },
    })
    return tokens(result)
  },
  async refresh(config: CognitoConfig, refreshToken: string) {
    const result = await call<AuthResult>(config, 'InitiateAuth', {
      AuthFlow: 'REFRESH_TOKEN_AUTH', ClientId: config.client_id, AuthParameters: { REFRESH_TOKEN: refreshToken },
    })
    return tokens(result, refreshToken)
  },
  signUp(config: CognitoConfig, name: string, email: string, password: string) {
    return call(config, 'SignUp', {
      ClientId: config.client_id, Username: email, Password: password,
      UserAttributes: [{ Name: 'email', Value: email }, { Name: 'name', Value: name }],
    })
  },
  confirm(config: CognitoConfig, email: string, code: string) {
    return call(config, 'ConfirmSignUp', { ClientId: config.client_id, Username: email, ConfirmationCode: code })
  },
  resendCode(config: CognitoConfig, email: string) {
    return call(config, 'ResendConfirmationCode', { ClientId: config.client_id, Username: email })
  },
  signOut(config: CognitoConfig, accessToken: string) {
    return call(config, 'GlobalSignOut', { AccessToken: accessToken }).catch(() => undefined)
  },
}

export function decodeJwt(token: string): Record<string, any> {
  try {
    const payload = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')
    return JSON.parse(decodeURIComponent(escape(atob(payload))))
  } catch {
    return {}
  }
}
