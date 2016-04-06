package main

import (
    "os"
    "net/http"
    "github.com/labstack/echo"
    "github.com/labstack/echo/engine/standard"
)

func main() {
    e := echo.New()
    e.Get("/", func(c echo.Context) error {
        return c.String(http.StatusOK, "Hello, World!")
    })
    e.Run(standard.New(":" + os.Getenv("PORT")))
}