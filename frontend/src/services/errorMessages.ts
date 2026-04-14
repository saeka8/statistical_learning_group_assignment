import { ApiRequestError } from './api';

type ErrorContext =
  | 'auth'
  | 'upload'
  | 'analysis'
  | 'workspaceDownload'
  | 'workspaceDelete'
  | 'workspaceRerun';

export function getUserFacingError(
  error: unknown,
  context: ErrorContext,
  fallback: string
): string {
  if (error instanceof ApiRequestError) {
    if (context === 'upload' && error.code === 'UNSUPPORTED_MEDIA_TYPE') {
      return 'Supported document types are PDF, PNG, JPG, JPEG, and TXT.';
    }

    if (context === 'workspaceDownload' && error.code === 'NOT_FOUND') {
      return 'We could not download that document.';
    }

    if (context === 'workspaceDelete' && error.code === 'NOT_FOUND') {
      return 'We could not delete that document.';
    }

    if (context === 'workspaceRerun' && error.code === 'UNPROCESSABLE') {
      return 'This document is already being processed.';
    }

    return error.message;
  }

  if (error instanceof Error && error.message) {
    return error.message;
  }

  return fallback;
}
