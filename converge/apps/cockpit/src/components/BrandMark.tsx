export function BrandMark() {
  return (
    <div className="brand" role="img" aria-label="Converge Cockpit">
      <picture aria-hidden="true">
        <source
          media="(max-width: 760px)"
          srcSet="/brand/converge-icon-color-light.svg"
          width="36"
          height="36"
        />
        <img
          src="/brand/converge-lockup-color-light.svg"
          alt=""
          width="190"
          height="48"
        />
      </picture>
      <span className="brand__surface" aria-hidden="true">
        Cockpit
      </span>
    </div>
  );
}
