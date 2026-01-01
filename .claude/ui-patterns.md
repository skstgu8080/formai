# UI/Styling Guidelines

> Theme-aware patterns for FormAI's Tailwind CSS components

## Button Styling (Critical)

### Action Buttons (Primary Interactive)
**USE:** `bg-secondary hover:bg-secondary/90 text-secondary-foreground`

```html
<!-- CORRECT -->
<button class="bg-secondary hover:bg-secondary/90 text-secondary-foreground px-4 py-2 rounded-md">
    Start Camera
</button>

<!-- WRONG: Will appear white in dark mode -->
<button class="bg-primary hover:bg-primary/90 text-primary-foreground">
    Action Button
</button>
```

### Destructive Actions (Delete, Stop, Cancel)
**USE:** `bg-destructive hover:bg-destructive/90 text-destructive-foreground`

### Status Badges
**OK to use:** Fixed colors like `bg-green-500`, `bg-red-500` with `text-white`

---

## Theme Color Reference

| Class | Light Mode | Dark Mode |
|-------|------------|-----------|
| `bg-primary` | Dark | Light (white!) |
| `bg-secondary` | Light gray | Dark gray |
| `bg-destructive` | Red | Red |

**Key Rule:** `bg-primary` inverts between modes. Use `bg-secondary` for consistent colored buttons.

---

## Common Patterns

### Cards
```html
<div class="bg-card text-card-foreground rounded-lg border shadow-sm p-4">
    Content
</div>
```

### Inputs
```html
<input class="bg-background border border-input text-foreground rounded-md px-3 py-2
              focus:outline-none focus:ring-2 focus:ring-ring">
```

### Muted Text
```html
<p class="text-muted-foreground text-sm">Secondary info</p>
```

---

## Page Requirements

Every HTML page in `web/` must include:
```html
<script src="/static/js/sidebar.js"></script>
<script src="/static/js/system-status.js"></script>
```

- `sidebar.js` - Renders navigation sidebar
- `system-status.js` - Populates footer (Browser, WebSocket, Memory, Version)
