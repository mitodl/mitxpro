// Creator: k6 Browser Recorder 0.6.0

import { sleep, group } from "k6";
import http from "k6/http";

export const options = {};

export default function main() {
  let response;

  group("page_2 - http://xpro.odl.local:8053/catalog/", function () {
    for (let i = 0; i < 10; i++) {
      response = http.get("http://xpro.odl.local:8053/catalog/", {
        headers: {
          host: "xpro.odl.local:8053",
          "user-agent":
            "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:107.0) Gecko/20100101 Firefox/107.0",
          accept:
            "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
          "accept-language": "en-US,en;q=0.5",
          "accept-encoding": "gzip, deflate",
          connection: "keep-alive",
          cookie:
            "csrftoken=fdY1Ywpf39ohyKG3wTNAGGGHkFGSKAzH5oCKLtfiQ9NuWHrTh0JHVNljUKiMG7IV; sessionid=.eJxVjDsOwjAQBe_iGlnxf6Gkzxksr3eNA8iR4qRC3B0ipYD2zcx7iZi2tcat8xInEhehxOl3w5Qf3HZA99Rus8xzW5cJ5a7Ig3Y5zsTP6-H-HdTU67e2gyKmgsAlaOOd8mzQIzijLThwweYQAFwiCoNVdGYwbAqSIc6kUbw_2po4GA:1ozibr:f80fQ7ovkY4wsmpk1DugFyxzjm7bgrRXbDKVQ8J8b7c",
          "upgrade-insecure-requests": "1",
        },
      });
    }
  });

  // Automatically added sleep
  sleep(1);
}
