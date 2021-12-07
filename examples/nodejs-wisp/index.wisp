#!/usr/bin/env wisp

(def express (require "express"))
(def expressws (require "express-ws"))
(def fs (require "fs"))
(let [app (express)
      ews (expressws app)
      port (or (aget process.env "PORT") 8000)
      host (or (aget process.env "BIND_ADDRESS") "127.0.0.1")]

  (app.get "/"
           (fn [req res]
             (res.sendFile (+ __dirname "/index.html"))))

  (app.ws "/ws"
          (fn [ws req]
            (ws.on "message"
                   (fn [msg]
                     (console.log "Got message:" msg)
                     (.map (.-clients (ews.getWss)) 
                           (fn [c]
                             (c.send msg)))))
            (ws.on "close" (fn [] (console.log "WebSocket was closed")))))

  (app.listen port host (fn [] (console.log "App launched."))))

