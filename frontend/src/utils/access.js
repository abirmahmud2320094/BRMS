export function hasAllowedRole(user, allowedRoles) {
  return Boolean(user?.role && allowedRoles.includes(user.role))
}

export function isAdministrator(user) {
  return hasAllowedRole(user, ['administrator'])
}
