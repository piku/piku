#!/usr/bin/env nodejs

const express = require('express');
const expressws = require('express-ws');
const fs = require('fs');
const app = express();

const ews = expressws(app);

app.get('/', (req, res) => {
  res.sendFile(__dirname + "/index.html");
});

app.ws('/ws', (ws, req) => {
  ws.on('message', msg => {
    console.log("Got message:", msg);
    ews.getWss().clients.map(function(c) {
      c.send(msg);
    });
  });

  ws.on('close', () => {
    console.log('WebSocket was closed');
  });
})

var port = process.env["PORT"] || 8000;
var addr = process.env["BIND_ADDRESS"] || "127.0.0.1";
console.log("Starting app on " + addr + ":" + port);
app.listen(port, addr, () => console.log('App launched.'));
