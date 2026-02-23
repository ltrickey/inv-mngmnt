import {
  CognitoUserPool,
  CognitoUser,
  AuthenticationDetails,
} from 'amazon-cognito-identity-js'

const POOL_DATA = {
  UserPoolId: import.meta.env.VITE_COGNITO_USER_POOL_ID || '',
  ClientId: import.meta.env.VITE_COGNITO_APP_CLIENT_ID || '',
}

let userPool = null
function getPool() {
  if (!userPool && POOL_DATA.UserPoolId && POOL_DATA.ClientId) {
    userPool = new CognitoUserPool(POOL_DATA)
  }
  return userPool
}

export function login(username, password) {
  return new Promise((resolve, reject) => {
    const pool = getPool()
    if (!pool) return reject(new Error('Cognito not configured'))

    const user = new CognitoUser({ Username: username, Pool: pool })
    const authDetails = new AuthenticationDetails({
      Username: username,
      Password: password,
    })

    user.authenticateUser(authDetails, {
      onSuccess: (session) => resolve({ session, user }),
      onFailure: (err) => reject(err),
      newPasswordRequired: (userAttributes) => {
        resolve({ newPasswordRequired: true, user, userAttributes })
      },
    })
  })
}

export function completeNewPassword(cognitoUser, newPassword) {
  return new Promise((resolve, reject) => {
    cognitoUser.completeNewPasswordChallenge(newPassword, {}, {
      onSuccess: (session) => resolve({ session, user: cognitoUser }),
      onFailure: (err) => reject(err),
    })
  })
}

export function getIdToken() {
  const pool = getPool()
  if (!pool) return null
  const user = pool.getCurrentUser()
  if (!user) return null

  return new Promise((resolve) => {
    user.getSession((err, session) => {
      if (err || !session?.isValid()) return resolve(null)
      resolve(session.getIdToken().getJwtToken())
    })
  })
}

export function logout() {
  const pool = getPool()
  if (!pool) return
  const user = pool.getCurrentUser()
  if (user) user.signOut()
}

export function getCurrentUser() {
  const pool = getPool()
  return pool ? pool.getCurrentUser() : null
}

export function isConfigured() {
  return !!(POOL_DATA.UserPoolId && POOL_DATA.ClientId)
}
