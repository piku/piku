package app.book;

import com.google.common.collect.*;
import java.util.*;

public class BookDao {

    private final List<Book> books = ImmutableList.of(
            new Book("Moby Dick", "Herman Melville", "9789583001215"),
            new Book("A Christmas Carol", "Charles Dickens", "9780141324524"),
            new Book("Pride and Prejudice", "Jane Austen", "9781936594290"),
            new Book("The Fellowship of The Ring", "J. R. R. Tolkien", "0007171978"),
            new Book("Harry Potter", "J. K. Rowling", "0747532699"),
            new Book("War and Peace", "Leo Tolstoy", "9780060798871"),
            new Book("Don Quixote", "Miguel Cervantes", "9789626345221"),
            new Book("Ulysses", "James Joyce", "9780394703800"),
            new Book("The Great Gatsby", "F. Scott Fitzgerald", "9780743273565"),
            new Book("One Hundred Years of Solitude", "Gabriel Garcia Marquez", "9780060531041"),
            new Book("The adventures of Huckleberry Finn", "Mark Twain", "9781591940296"),
            new Book("Alice In Wonderland", "Lewis Carrol", "9780439291491")
    );

    public Iterable<Book> getAllBooks() {
        return books;
    }

    public Book getBookByIsbn(String isbn) {
        return books.stream().filter(b -> b.getIsbn().equals(isbn)).findFirst().orElse(null);
    }

    public Book getRandomBook() {
        return books.get(new Random().nextInt(books.size()));
    }
}
