export function formatApiError(error, fallbackMessage) {
  if (error?.payload?.detail?.message) {
    return error.payload.detail.message;
  }
  if (typeof error?.payload?.detail === 'string') {
    return error.payload.detail;
  }
  if (typeof error?.payload?.message === 'string') {
    return error.payload.message;
  }
  if (typeof error?.message === 'string' && error.message.trim()) {
    return error.message;
  }
  return fallbackMessage;
}
