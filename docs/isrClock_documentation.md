# isrClock.h — Documentation

Minimal ISR-based clock generator (Timer1) and support for sequential logic on **ATmega32u4** boards (e.g., Adafruit ItsyBitsy 32u4 5V).

## Purpose

`isrClock.h` provides:

1. **Internal clock generation (optional)**  
   Uses **Timer1** in CTC mode to output a square wave on a user-defined pin.

2. **Support for sequential logic**  
   Designed to integrate with generated `.ino` code that updates D‑type flip‑flops on rising clock edges.

The library is extremely small and intended for inclusion directly next to generated Arduino sketches.

---

## Configuration Macros

These must be defined **before including** `isrClock.h`:

```cpp
#ifndef USE_INTERNAL_CLOCK
#define USE_INTERNAL_CLOCK 0
#endif

#ifndef CLOCK_HZ
#define CLOCK_HZ 10
#endif

#ifndef PIN_CLK
#define PIN_CLK 4
#endif

#ifndef CLOCK_LED_MIRROR
#define CLOCK_LED_MIRROR 0
#endif
```

### USE_INTERNAL_CLOCK
- `1` → Timer1 generates a square wave on `PIN_CLK`.  
- `0` → Clock is assumed to be supplied externally.

### CLOCK_HZ
Frequency (in Hz) of the internal clock.

### PIN_CLK
Digital pin used for clock output/input.

### CLOCK_LED_MIRROR
Mirrors the internal clock to the built‑in LED (on pin 13) when set to `1`.

---

## Public Function

### `void T1Clock_begin(uint8_t pin_clk, uint16_t hz);`

Starts Timer1 and toggles `pin_clk` at the given frequency.

**Parameters**

- `pin_clk` – clock pin (typically PIN_CLK)  
- `hz` – target clock frequency

This configures Timer1 in CTC mode and sets up an interrupt that toggles the pin and optionally mirrors it to LED (pin 13).

---

## Internal Behavior

- Chooses appropriate Timer1 prescaler and compare match values.
- ISR toggles the clock pin.
- Optional LED mirroring.

Example ISR pattern:

```cpp
ISR(TIMER1_COMPA_vect) {
    state = !state;
    digitalWrite(clk_pin, state);
    if (mirror) digitalWrite(13, state);
}
```

---

## Example Arduino Sketch Integration

```cpp
#define USE_INTERNAL_CLOCK   1
#define CLOCK_HZ             2
#define PIN_CLK              4
#define CLOCK_LED_MIRROR     1

#include "isrClock.h"

int __clk_prev = LOW;

void setup() {
    pinMode(PIN_CLK, INPUT);
    __clk_prev = digitalRead(PIN_CLK);

#if USE_INTERNAL_CLOCK
    T1Clock_begin(PIN_CLK, CLOCK_HZ);
#endif
}

void loop() {
    int clk_now = digitalRead(PIN_CLK);
    bool rising = (__clk_prev == LOW && clk_now == HIGH);
    __clk_prev = clk_now;

    // combinational logic here
    // compute D-inputs here

    if (rising) {
        // update Q registers here
    }
}
```

---

## Notes & Limitations

- Designed for **low frequencies (1–10 Hz)** suitable for teaching and visualization.
- Uses `digitalWrite()` inside ISR: simple but not optimized for high‑speed clocks.
- If `USE_INTERNAL_CLOCK == 1`, Timer1 is not available for other libraries (Servo, tone, etc.).
- External-clock mode does not modify Timer1.

---

## File Placement

Your deployment process expects:

```
<SketchDir>/isrClock.h
```

When generating a sketch, the application copies this file automatically into:

```
<SketchDir>/seq_sketch/isrClock.h
```

so the compiler can find it.

---
