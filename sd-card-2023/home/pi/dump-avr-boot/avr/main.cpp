#include <avr/io.h>
#include <avr/pgmspace.h>
#include <avr/interrupt.h>
#include <avr/wdt.h>

inline void loop()
{
    wdt_reset();

    // Return unless we've received a byte on serial port
    if (!(UCSR1A & _BV(RXC1)))
    {
        while (!(UCSR1A & _BV(UDRE1)))
            ;
        return;
    }

    PORTC &= ~_BV(7);

    // Read byte from serial port
    (void)UDR1;

    // Read flash out to serial port
    uint16_t i = 0;
    do
    {
        wdt_reset();
        const uint8_t b = pgm_read_byte(i);
        while (!(UCSR1A & _BV(UDRE1)))
            ;
        UDR1 = b;
    } while (++i <= 0x8000);
}

int main()
{
    cli();

    // Enable LED output
    DDRC |= _BV(7);
    // Turn on LED
    PORTC |= _BV(7);

    // Enable ouptut on Tx pin
    DDRD |= _BV(3);
    // Ensure Rx is input and pulled up
    DDRD &= ~_BV(2);
    PORTD |= _BV(2);

    // setup serial port for 1MBaud (from 16MHz clock)
    UBRR1H = 0;
    UBRR1L = 0;
    // Default 8-bit mode, 1 stop bit, no parity
    UCSR1D = 0;
    UCSR1C = 0b00000110;
    UCSR1B = _BV(TXEN1) | _BV(RXEN1);
    UCSR1A = 0;

    // main loop
    while (true)
    {
        loop();
    }
}