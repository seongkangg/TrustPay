// Small outline icon set (24px grid, 1.75 stroke) for the nav and the few labelled affordances.
function Icon({ size = 18, children, ...rest }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      {...rest}
    >
      {children}
    </svg>
  );
}

export const HomeIcon = (p) => (
  <Icon {...p}>
    <path d="M4 10.5 12 4l8 6.5V19a1 1 0 0 1-1 1h-4.5v-5.5h-5V20H5a1 1 0 0 1-1-1z" />
  </Icon>
);

export const ApprovalIcon = (p) => (
  <Icon {...p}>
    <circle cx="12" cy="12" r="8" />
    <path d="m8.5 12.2 2.4 2.3 4.6-4.8" />
  </Icon>
);

export const InboxIcon = (p) => (
  <Icon {...p}>
    <path d="M4 13.5 6.4 5.6A1 1 0 0 1 7.4 5h9.2a1 1 0 0 1 1 .6l2.4 7.9V18a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1z" />
    <path d="M4 13.5h4.5l1.2 2h4.6l1.2-2H20" />
  </Icon>
);

export const ListIcon = (p) => (
  <Icon {...p}>
    <path d="M9 7h11M9 12h11M9 17h11" />
    <path d="M4.5 7h.01M4.5 12h.01M4.5 17h.01" strokeWidth="2.5" />
  </Icon>
);

export const CalendarIcon = (p) => (
  <Icon {...p}>
    <rect x="4" y="5.5" width="16" height="14" rx="2" />
    <path d="M4 10h16M8.5 3.5v4M15.5 3.5v4" />
  </Icon>
);

export const ArrowUpIcon = (p) => (
  <Icon size={12} strokeWidth="2.25" {...p}>
    <path d="M12 19V5M6 11l6-6 6 6" />
  </Icon>
);

export const ChevronRightIcon = (p) => (
  <Icon size={16} {...p}>
    <path d="m9.5 6 6 6-6 6" />
  </Icon>
);

// TrustPay mark: a rounded indigo tile with a tick, the "approved" stroke the product is about.
export function Mark({ size = 28 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 28 28" aria-hidden="true">
      <rect width="28" height="28" rx="8" fill="var(--accent)" />
      <path
        d="M8 14.4 12.2 18.5 20 9.8"
        fill="none"
        stroke="#fff"
        strokeWidth="2.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
