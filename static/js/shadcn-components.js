/**
 * shadcn/ui Components for FormAI
 * Vanilla JavaScript implementation of shadcn/ui components
 */

// Utility function for class merging (similar to cn from shadcn/ui)
function cn(...classes) {
  return classes.filter(Boolean).join(' ');
}

// Button component
class Button {
  constructor(element, options = {}) {
    this.element = element;
    this.variant = options.variant || 'default';
    this.size = options.size || 'default';
    this.className = options.className || '';
    
    this.init();
  }

  init() {
    const baseClasses = 'inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50';
    
    const variantClasses = {
      default: 'bg-primary text-primary-foreground hover:bg-primary/90',
      destructive: 'bg-destructive text-destructive-foreground hover:bg-destructive/90',
      outline: 'border border-input bg-background hover:bg-accent hover:text-accent-foreground',
      secondary: 'bg-secondary text-secondary-foreground hover:bg-secondary/80',
      ghost: 'hover:bg-accent hover:text-accent-foreground',
      link: 'text-primary underline-offset-4 hover:underline'
    };

    const sizeClasses = {
      default: 'h-10 px-4 py-2',
      sm: 'h-9 rounded-md px-3',
      lg: 'h-11 rounded-md px-8',
      icon: 'h-10 w-10'
    };

    const classes = cn(
      baseClasses,
      variantClasses[this.variant],
      sizeClasses[this.size],
      this.className
    );

    this.element.className = classes;
  }
}

// Card component
class Card {
  constructor(element, options = {}) {
    this.element = element;
    this.className = options.className || '';
    this.init();
  }

  init() {
    const classes = cn(
      'rounded-lg border bg-card text-card-foreground shadow-sm',
      this.className
    );
    this.element.className = classes;
  }
}

// Input component
class Input {
  constructor(element, options = {}) {
    this.element = element;
    this.className = options.className || '';
    this.init();
  }

  init() {
    const classes = cn(
      'flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50',
      this.className
    );
    this.element.className = classes;
  }
}

// Label component
class Label {
  constructor(element, options = {}) {
    this.element = element;
    this.className = options.className || '';
    this.init();
  }

  init() {
    const classes = cn(
      'text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70',
      this.className
    );
    this.element.className = classes;
  }
}

// Select component
class Select {
  constructor(element, options = {}) {
    this.element = element;
    this.className = options.className || '';
    this.init();
  }

  init() {
    const classes = cn(
      'flex h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50',
      this.className
    );
    this.element.className = classes;
  }
}

// Badge component
class Badge {
  constructor(element, options = {}) {
    this.element = element;
    this.variant = options.variant || 'default';
    this.className = options.className || '';
    this.init();
  }

  init() {
    const baseClasses = 'inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2';
    
    const variantClasses = {
      default: 'border-transparent bg-primary text-primary-foreground hover:bg-primary/80',
      secondary: 'border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80',
      destructive: 'border-transparent bg-destructive text-destructive-foreground hover:bg-destructive/80',
      outline: 'text-foreground'
    };

    const classes = cn(
      baseClasses,
      variantClasses[this.variant],
      this.className
    );

    this.element.className = classes;
  }
}

// Alert component
class Alert {
  constructor(element, options = {}) {
    this.element = element;
    this.variant = options.variant || 'default';
    this.className = options.className || '';
    this.init();
  }

  init() {
    const baseClasses = 'relative w-full rounded-lg border p-4 [&>svg~*]:pl-7 [&>svg+div]:translate-y-[-3px] [&>svg]:absolute [&>svg]:left-4 [&>svg]:top-4 [&>svg]:text-foreground';
    
    const variantClasses = {
      default: 'bg-background text-foreground',
      destructive: 'border-destructive/50 text-destructive dark:border-destructive [&>svg]:text-destructive'
    };

    const classes = cn(
      baseClasses,
      variantClasses[this.variant],
      this.className
    );

    this.element.className = classes;
  }
}

// Utility functions for creating components
window.ShadcnUI = {
  Button,
  Card,
  Input,
  Label,
  Select,
  Badge,
  Alert,
  cn
};

// Auto-initialize components when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
  // Initialize buttons with data-shadcn attributes
  document.querySelectorAll('[data-shadcn="button"]').forEach(element => {
    const variant = element.dataset.variant || 'default';
    const size = element.dataset.size || 'default';
    new Button(element, { variant, size });
  });

  // Initialize cards with data-shadcn attributes
  document.querySelectorAll('[data-shadcn="card"]').forEach(element => {
    new Card(element);
  });

  // Initialize inputs with data-shadcn attributes
  document.querySelectorAll('[data-shadcn="input"]').forEach(element => {
    new Input(element);
  });

  // Initialize labels with data-shadcn attributes
  document.querySelectorAll('[data-shadcn="label"]').forEach(element => {
    new Label(element);
  });

  // Initialize selects with data-shadcn attributes
  document.querySelectorAll('[data-shadcn="select"]').forEach(element => {
    new Select(element);
  });

  // Initialize badges with data-shadcn attributes
  document.querySelectorAll('[data-shadcn="badge"]').forEach(element => {
    const variant = element.dataset.variant || 'default';
    new Badge(element, { variant });
  });

  // Initialize alerts with data-shadcn attributes
  document.querySelectorAll('[data-shadcn="alert"]').forEach(element => {
    const variant = element.dataset.variant || 'default';
    new Alert(element, { variant });
  });
});
