# Brand

## Fonts

From Google Fonts:

- **Headings and body**: Instrument Sans. Headings use tight tracking (-0.02em) and weight 600.
- **Accent (a tagline or a quote)**: Instrument Serif, italic
- **Code, numbers and identifiers**: Geist Mono. Use tabular figures for numbers in tables.

## Colors

Most of the page is neutral. Jade is the only accent in everyday UI. The other colors are for charts and status.

### Neutrals

| Role | Light mode | Dark mode |
|---|---|---|
| Page background | `#F5F7F7` | `#0B1416` |
| Panels and cards | `#FFFFFF` | `#141F22` |
| Raised (menus, popovers) | `#FFFFFF` with soft shadow | `#1C292D` |
| Ink | `#0B1F24` | `#E6EEF0` |
| Muted text | `#5A6A6F` | `#93A5AA` |

### Accent

- **Jade** `#14C08F`, Ink text. For buttons, links and the active state.
- Jade text on light backgrounds: `#04795B`. On dark: `#4FDDB2`.

### Charts and status

1. Jade `#14C08F`, Ink text
2. Amber `#F2B544`, Ink text
3. Coral `#F2876A`, Ink text
4. Cerulean `#1675A5`, white text (also for information)
5. Raspberry `#C93558`, white text (also for errors and alerts)

Use them in that order. Amber text on light backgrounds: `#9A6500`. On dark: `#F7CA6E`.

## Surfaces

- Panels have 12px radius, controls 8px and pills fully round.
- No outlines. In light mode, panels sit on the page with a soft shadow (`0 1px 2px rgb(11 31 36 / 0.06)`). In dark mode, they sit on the page using a lighter surface and no shadow.
- Spacing on a 4px grid, with generous whitespace (24px or more inside panels).

## Avoid

- Borders on one edge of a panel, and thin lines across the top of the page
- Gradient fills, except a very subtle one on a hero background
- More than one bright color in a single non-chart component

## Tone

Plain business English in US spelling. Short labels, no jargon and no exclamation marks. Money is in AUD dollars, such as $1,250.00.