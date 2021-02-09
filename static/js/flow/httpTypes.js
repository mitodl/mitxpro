export type HttpRespErrorMessage = string | Array<string> | Object | null

export type HttpResponse<T> = {
  body:
    | T
    | {
        errors: HttpRespErrorMessage
      },
  status: number
}
