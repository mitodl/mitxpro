import { getCookie } from "../api"
import type {updateEmailResponse} from "../../flow/authTypes";
import type {DigitalCredential} from "../../flow/courseTypes";

export default {
  downloadDigitalCredentials: (uuid: string, isCourse: boolean) => ({
    queryKey:  "digitalCredentialDownload",
    url:       `/api/v1/${isCourse ? "course_run_certificates" : "program_certificates"}/${uuid}/request-digital-credential/`,
    transform: (json: DigitalCredential) => ({
      digitalCredential: json
    }),
    update: {
      digitalCredential: (prev: DigitalCredential, next: DigitalCredential) =>
        next
    },
    body:     {},
    options:  {
      method:  "POST",
      headers: {
        "X-CSRFTOKEN": getCookie("csrftoken")
      }
    }
  })
}
