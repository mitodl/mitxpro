// Install version of yarn specified in package.json

const fs = require('fs');
const { engines: { yarn: yarnVersion }} = JSON.parse(fs.readFileSync(__dirname + "/../package.json"));

console.log(yarnVersion)
