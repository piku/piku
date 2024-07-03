use std::{io::Write, net::TcpListener};

fn main() -> std::io::Result<()> {
    let addr = format!("{}:{}", 
        std::env::var("BIND_ADDRESS").expect("no addr"), 
        std::env::var("PORT").expect("no port"));
        
    println!("Listening on {}", addr);
    let listener = TcpListener::bind(addr)?;

    for stream in listener.incoming() {
        let mut stream = stream?;
        stream.write_all(b"Hello!\n")?;
    }

    Ok(())
}
