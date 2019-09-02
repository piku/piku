package demo;

import java.util.concurrent.TimeUnit;

/**
*This is a simple threaded worker
*
*@author John Simiyu
*/

class Worker {
	public static void main(String[] args) {

		System.out.println("Feel the magic of a Worker");

        for(int i=1;i<=20;i++){  
			System.out.println(i);
			System.out.println("Pausing for 10 Seconds!");

			try {
			TimeUnit.SECONDS.sleep(10);
			} catch (InterruptedException e) {
				e.printStackTrace();
			}
		}

		System.out.println("Back to work..because I am a Worker!");
	}
}