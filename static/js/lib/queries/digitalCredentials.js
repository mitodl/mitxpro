import { getCookie } from "../api"

export default {
  requestDigitalCredentials: (uuid: string, isCourse: boolean) => ({
    queryKey: "digitalCredentialDownload",
    url:      `/api/v1/${
      isCourse ? "course_run_certificates" : "program_certificates"
    }/${uuid}/request-digital-credential/`,
    update:  {},
    body:    {},
    options: {
      method:  "POST",
      headers: {
        "X-CSRFTOKEN": getCookie("csrftoken")
      }
    }
  })
}
