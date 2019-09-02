package demo;

import java.io.*;
import java.net.*;
import java.util.Date;

import io.github.cdimascio.dotenv.Dotenv;
 
/**
 * This program demonstrates a simple TCP/IP socket server.
 *
 * @author John Simiyu
 */
public class TimeServer {
 
    public static void main(String[] args) {

        Dotenv dotenv = Dotenv.configure()
        .filename("ENV")
        .ignoreIfMalformed()
        .ignoreIfMissing()
        .load();
        int port = Integer.parseInt(dotenv.get("PORT"));
 
        try (ServerSocket serverSocket = new ServerSocket(port)) {
 
            System.out.println("Server is listening on port: " + port);
 
            while (true) {
                Socket socket = serverSocket.accept();
 
                System.out.println("New client connected: Timestamp sent to client!");
 
                OutputStream output = socket.getOutputStream();
                PrintWriter writer = new PrintWriter(output, true);
 
                writer.println(new Date().toString());
            }
 
        } catch (IOException ex) {
            System.out.println("Server exception: " + ex.getMessage());
            ex.printStackTrace();
        }
    }
}