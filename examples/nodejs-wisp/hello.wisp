#!/usr/bin/env wisp

(console.log "Hello from Wisp!")
(console.log process.argv)
(console.log "Express library present?" (if (require "express") "express exists" "express missing"))
