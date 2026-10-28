/**
 * Case File export (backend/case_file.py via main.py's
 * GET /api/cases/{id}/case-file.{pdf,docx}). The file is generated on
 * request and streamed back; nothing is stored server-side, so there is no
 * file id to fetch later -- each download regenerates it.
 */
export class CaseFileError extends Error {
  constructor(message, status) {
    super(message);
    this.name = 'CaseFileError';
    this.status = status;
  }

  /** 503 from the PDF endpoint = LibreOffice isn't installed; the DOCX still works. */
  get pdfUnavailable() {
    return this.status === 503;
  }
}

function filenameFromDisposition(response, fallback) {
  const disposition = response.headers.get('content-disposition') || '';
  const match = /filename="?([^"]+)"?/i.exec(disposition);
  return match ? match[1] : fallback;
}

export async function downloadCaseFile(caseId, format) {
  let response;
  try {
    response = await fetch(`/api/cases/${encodeURIComponent(caseId)}/case-file.${format}`);
  } catch {
    throw new CaseFileError("Couldn't reach Legal Aid AI. Make sure the backend is running.", 0);
  }
  if (!response.ok) {
    let detail;
    try {
      const body = await response.json();
      detail = typeof body?.detail === 'string' ? body.detail : undefined;
    } catch {
      // non-JSON error body; fall through to the generic message
    }
    throw new CaseFileError(detail || `The case file could not be created (HTTP ${response.status}).`, response.status);
  }
  const blob = await response.blob();
  return { blob, filename: filenameFromDisposition(response, `case-file.${format}`) };
}
