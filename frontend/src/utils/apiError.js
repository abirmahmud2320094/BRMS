const NETWORK_ERROR_PATTERN = /failed to fetch|networkerror|network request failed|load failed/i

function cleanMessage(message) {
  return String(message).replace(/^value error,\s*/i, '').trim()
}

function fieldLabel(location) {
  if (!Array.isArray(location) || !location.length) return ''
  const field = location[location.length - 1]
  if (typeof field !== 'string') return ''
  return field
    .replace(/_/g, ' ')
    .replace(/\b\w/g, character => character.toUpperCase())
    .replace(/\bId\b/g, 'ID')
}

function extractMessage(value, seen = new WeakSet()) {
  if (typeof value === 'string' || typeof value === 'number') {
    return cleanMessage(value)
  }
  if (!value) return ''

  if (Array.isArray(value)) {
    const messages = value.map(item => extractMessage(item, seen)).filter(Boolean)
    return [...new Set(messages)].join('; ')
  }

  if (typeof value === 'object') {
    if (seen.has(value)) return ''
    seen.add(value)

    if (typeof value.msg === 'string') {
      const message = cleanMessage(value.msg)
      const field = fieldLabel(value.loc)
      if (field && /^field required$/i.test(message)) return `${field} is required.`
      return message
    }

    for (const key of ['detail', 'message', 'error']) {
      const message = extractMessage(value[key], seen)
      if (message) return message
    }

    const messages = Object.values(value)
      .map(item => extractMessage(item, seen))
      .filter(Boolean)
    return [...new Set(messages)].join('; ')
  }

  return ''
}

export function getApiErrorMessage(error, fallback = 'Something went wrong. Please try again.') {
  if (error instanceof Error) {
    const responseMessage = extractMessage(error.body || error.response?.data)
    if (responseMessage) return responseMessage
    if (NETWORK_ERROR_PATTERN.test(error.message || '')) {
      return 'Unable to reach the server. Check your connection and try again.'
    }
    return cleanMessage(error.message) || fallback
  }

  const message = extractMessage(error)
  if (NETWORK_ERROR_PATTERN.test(message)) {
    return 'Unable to reach the server. Check your connection and try again.'
  }
  return message || fallback
}
