from core.exceptions import OrdinisException


class SupportAccessError(OrdinisException):
    code = 'SUPPORT_ACCESS_ERROR'
    message = 'This support access request cannot be changed.'
    status_code = 400


class SupportAccessRequired(OrdinisException):
    code = 'SUPPORT_ACCESS_REQUIRED'
    message = "No approved, unexpired support access for this company. Ask the company's CEO to approve a request."
    status_code = 403
