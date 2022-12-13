// Creator: k6 Browser Recorder 0.6.0
import { randomItem, randomIntBetween, normalDistributionStages } from 'https://jslib.k6.io/k6-utils/1.2.0/index.js';
import * as _ from 'https://cdnjs.cloudflare.com/ajax/libs/lodash.js/4.17.21/lodash.min.js'

import { sleep, group } from 'k6'
import http from 'k6/http'
import exec from 'k6/execution'


export const options = {}

export function setup() {
    let baseUrl = __ENV.BASE_URL

    if (!baseUrl) {
        console.log("BASE_URL is not specified")
        exec.test.abort()
    } 
    
    // remove trailing slash if it exists
    baseUrl = _.trim(baseUrl, '/')

    return {
        baseUrl,
        programs: http.get(`${baseUrl}/api/programs/`).json(),
        courses: http.get(`${baseUrl}/api/courses/`).json(),
    }
}

export default function main(data) {

    group("Home Page", () => {
        http.get(http.url`${data.baseUrl}/`)
        http.get(http.url`${data.baseUrl}/api/users/me`)

        group('Catalog Pages', () => {

            http.get(http.url`${data.baseUrl}/catalog/`)
            http.get(http.url`${data.baseUrl}/api/users/me`)

            _.times(randomIntBetween(1, 10), function() {

                if (randomIntBetween(0, 1) === 0) {
                    group("Program Page", function() {
                        const program = randomItem(data.programs)

                        http.get(http.url`${data.baseUrl}/programs/${program.readable_id}/`)
                        http.get(http.url`${data.baseUrl}/api/users/me`)
                    })
                } else {
                    group("Course Page", function() {
                        const course = randomItem(data.courses)

                        http.get(http.url`${data.baseUrl}/courses/${course.readable_id}/`)
                        http.get(http.url`${data.baseUrl}/api/users/me`)
                    })
                }

            })

        })

    })
}
