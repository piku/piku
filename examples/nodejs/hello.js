#!/usr/bin/env nodejs

console.log("Hello!");
console.log(process.argv)
console.log(require('express') ? "express exists" : "express missing");
