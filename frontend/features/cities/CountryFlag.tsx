/**
 * A country's flag by its ISO code (IN, CA), 4:3, `size` pixels high. The
 * pictures come from the flag-icons package (MIT), served with the console,
 * not from another site; emoji flags are not used because Windows shows them
 * as two letters. Nothing for a code that is not a country's.
 */
export default function CountryFlag({ code, size = 12 }: { code: string; size?: number }) {
  if (!/^[A-Za-z]{2}$/.test(code)) return null;
  return (
    <span
      aria-hidden="true"
      // flag-icons sizes the flag from the font size: 1em high, 4/3 em wide.
      style={{ fontSize: size }}
      className={`fi fi-${code.toLowerCase()} shrink-0 rounded-[2px] shadow-[0_0_0_1px_rgb(15_23_42/0.14)]`}
    />
  );
}
