/**
 * Hand-drawn line-art illustrations, authored as inline SVG.
 *
 * Deliberately not raster assets: they inherit `currentColor` so they follow
 * the theme, they stay sharp at any size, individual parts can be animated
 * (the question mark bobs, scan ticks pulse), and the whole set ships in the
 * bundle with no image requests.
 *
 * Shared stroke vocabulary, defined once in styles.css:
 *   .stroke      5px outline, round caps — the default line
 *   .thin        3.5px outline — interior detail
 *   .solid       filled with currentColor — hair, lips, dots
 *   .paper-fill  filled with the page colour — anything that must occlude
 *   .accent      soft lilac blob sitting behind the subject
 */

/** Loan officer weighing a stack of documents she can't fully verify. */
export function OfficerReviewing() {
  return (
    <svg
      className="doodle art-float"
      viewBox="0 0 900 470"
      role="img"
      aria-label="An officer looking uncertainly at a stack of loan documents on a stand, with a question mark above her."
    >
      <ellipse className="accent" cx="600" cy="252" rx="190" ry="196" />
      <path className="stroke" d="M28 442 H872" />

      {/* document stand */}
      <path className="stroke" d="M146 346 V438" />
      <path className="stroke" d="M300 350 V438" />
      <path className="stroke" d="M390 346 V438" />
      <path className="stroke" d="M104 346 L170 294 H300 V346 Z" />
      <path className="stroke" d="M300 294 H414 L430 346 H300 Z" />

      {/* left document */}
      <path className="paper-fill" d="M158 158 H300 V294 H158 Z" />
      <path className="stroke" d="M178 184 L229 216 L281 184" />
      <path className="stroke" d="M178 244 H256" />
      <path className="stroke" d="M178 266 H236" />
      <path className="thin" d="M158 226 C140 236 138 258 152 268" />

      {/* right document */}
      <path className="paper-fill" d="M300 148 H386 V294 H300 Z" />
      <path className="stroke" d="M316 190 H370" />
      <path className="stroke" d="M316 212 H370" />
      <path className="stroke" d="M316 234 H352" />
      <path className="stroke" d="M316 256 H370" />
      <path className="thin" d="M386 206 C404 216 406 238 392 248" />
      <path className="stroke" d="M300 148 C330 124 358 122 392 138 C372 148 364 166 388 178" />

      {/* figure */}
      <path
        className="solid"
        d="M600 86 C676 86 706 142 698 208 C704 254 694 296 686 318 L652 318
           C666 262 670 218 664 180 C656 136 636 118 600 118
           C564 118 544 136 536 180 C530 218 534 262 548 318 L514 318
           C506 296 496 254 502 208 C494 142 524 86 600 86 Z"
      />
      <ellipse className="paper-fill" cx="600" cy="176" rx="57" ry="70" />
      <path
        className="solid"
        d="M542 154 C546 110 566 92 600 92 C638 92 662 114 660 158
           C640 130 618 140 594 134 C570 128 553 136 542 154 Z"
      />
      <rect className="stroke" x="551" y="154" width="43" height="33" rx="11" />
      <rect className="stroke" x="606" y="154" width="43" height="33" rx="11" />
      <path className="stroke" d="M594 168 H606" />
      <path className="stroke" d="M551 164 L539 161" />
      <path className="stroke" d="M649 164 L659 163" />
      <path className="thin" d="M559 143 C570 134 586 134 594 141" />
      <path className="thin" d="M563 170 C569 177 578 177 583 170" />
      <path className="thin" d="M618 170 C624 177 633 177 638 170" />
      <path className="thin" d="M606 190 C601 200 606 205 613 204" />
      <path className="solid" d="M594 218 C604 212 618 214 623 220 C615 227 601 226 594 218 Z" />
      <path className="stroke" d="M576 242 V268" />
      <path className="stroke" d="M624 242 V268" />
      <path
        className="paper-fill"
        d="M576 268 L600 300 L624 268 C660 282 692 336 692 442 H508 C508 336 540 282 576 268 Z"
      />
      <path className="stroke" d="M576 268 L563 292 L590 286" />
      <path className="stroke" d="M624 268 L637 292 L610 286" />
      <path className="stroke" d="M600 300 V352" />
      <circle className="stroke" cx="600" cy="318" r="4" />
      <circle className="stroke" cx="600" cy="342" r="4" />
      <path className="stroke" d="M528 382 H570" />
      <path className="stroke" d="M630 382 H664" />

      <g id="qmark">
        <path className="stroke" d="M684 60 C686 40 718 38 722 56 C726 72 706 76 705 92" />
        <circle className="solid" cx="704" cy="108" r="4" />
      </g>

      <g className="scan">
        <path className="thin" d="M452 200 H478" />
        <path className="thin" d="M452 226 H470" />
        <path className="thin" d="M452 252 H478" />
      </g>
    </svg>
  );
}

/** The same face, two screens, opposite verdicts — the ensemble disagreeing. */
export function ModelsDisagree() {
  return (
    <svg
      className="doodle"
      viewBox="0 0 620 470"
      role="img"
      aria-label="Two screens showing the same face reaching opposite verdicts, with a person deciding between them."
    >
      <ellipse className="accent" cx="310" cy="230" rx="250" ry="180" />
      <path className="stroke" d="M24 440 H596" />

      {/* left screen — flagged fake */}
      <path className="paper-fill" d="M46 96 H262 V282 H46 Z" />
      <path className="stroke" d="M154 282 V318" />
      <path className="stroke" d="M112 318 H196" />
      <circle className="stroke" cx="154" cy="168" r="34" />
      <path className="stroke" d="M112 244 C112 208 196 208 196 244" />
      <path className="stroke" d="M96 122 L120 146 M120 122 L96 146" />
      <path className="thin" d="M212 238 H240 M212 258 H232" />

      {/* right screen — cleared real */}
      <path className="paper-fill" d="M358 96 H574 V282 H358 Z" />
      <path className="stroke" d="M466 282 V318" />
      <path className="stroke" d="M424 318 H508" />
      <circle className="stroke" cx="466" cy="168" r="34" />
      <path className="stroke" d="M424 244 C424 208 508 208 508 244" />
      <path className="stroke" d="M406 134 l14 14 l24 -28" />
      <path className="thin" d="M524 238 H552 M524 258 H544" />

      {/* the person left holding the decision */}
      <path
        className="solid"
        d="M310 336 C338 336 350 356 346 380 C348 396 344 410 341 420 L327 420
           C333 400 335 384 332 372 C328 356 322 350 310 350
           C298 350 292 356 288 372 C285 384 287 400 293 420 L279 420
           C276 410 272 396 274 380 C270 356 282 336 310 336 Z"
      />
      <ellipse className="paper-fill" cx="310" cy="374" rx="22" ry="27" />
      <path className="thin" d="M300 370 h7 M313 370 h7" />
      <path className="thin" d="M303 386 C307 390 313 390 317 386" />
      <path
        className="paper-fill"
        d="M296 402 L310 414 L324 402 C344 410 356 424 356 440 H264 C264 424 276 410 296 402 Z"
      />

      <path className="thin scan" d="M282 344 C244 330 214 312 200 300" />
      <path className="thin scan" d="M338 344 C376 330 406 312 420 300" />
    </svg>
  );
}

/** Customer on a call they cannot verify, with a spoofed handset alongside. */
export function ScamCall() {
  return (
    <svg
      className="doodle"
      viewBox="0 0 620 470"
      role="img"
      aria-label="A person on a phone call wondering whether the caller is genuine."
    >
      <ellipse className="accent" cx="310" cy="240" rx="240" ry="190" />
      <path className="stroke" d="M24 440 H596" />

      {/* spoofed handset with a warning */}
      <path className="paper-fill" d="M64 176 H186 V346 H64 Z" />
      <path className="stroke" d="M64 208 H186" />
      <path className="thin" d="M86 258 H164 M86 282 H146 M86 306 H164" />
      <circle className="stroke" cx="80" cy="192" r="5" />
      <path className="stroke" d="M125 118 L152 166 H98 Z" />
      <path className="thin" d="M125 134 V148" />
      <circle className="solid" cx="125" cy="157" r="3.5" />

      {/* customer */}
      <path
        className="solid"
        d="M380 138 C452 138 480 190 472 250 C478 292 468 330 461 350 L430 350
           C443 298 447 258 441 222 C434 182 415 166 380 166
           C346 166 328 182 321 222 C315 258 319 298 332 350 L301 350
           C294 330 284 292 290 250 C282 190 310 138 380 138 Z"
      />
      <ellipse className="paper-fill" cx="380" cy="224" rx="52" ry="64" />
      <path
        className="solid"
        d="M327 204 C331 164 350 146 380 146 C414 146 436 166 434 206
           C416 180 396 190 374 184 C352 178 337 187 327 204 Z"
      />
      <rect className="stroke" x="334" y="204" width="38" height="29" rx="10" />
      <rect className="stroke" x="384" y="204" width="38" height="29" rx="10" />
      <path className="stroke" d="M372 217 H384" />
      <path className="thin" d="M345 218 C350 224 358 224 362 218" />
      <path className="thin" d="M395 218 C400 224 408 224 412 218" />
      <path className="thin" d="M386 240 C382 249 386 253 392 252" />
      <path className="thin" d="M368 268 C378 262 392 264 397 270" />
      <path className="stroke" d="M358 284 V306" />
      <path className="stroke" d="M402 284 V306" />
      <path
        className="paper-fill"
        d="M358 306 L380 334 L402 306 C436 318 464 364 464 440 H296 C296 364 324 318 358 306 Z"
      />
      <path className="stroke" d="M358 306 L347 328 L371 322" />
      <path className="stroke" d="M402 306 L413 328 L389 322" />

      {/* handset held to the ear */}
      <path className="paper-fill" d="M436 206 H468 V262 H436 Z" />
      <path className="thin" d="M444 216 H460 M444 228 H460" />
      <path className="stroke" d="M446 320 C470 306 472 282 466 264" />

      <g id="qmark2">
        <path className="stroke" d="M502 136 C504 116 536 114 540 132 C544 148 524 152 523 168" />
        <circle className="solid" cx="522" cy="184" r="4" />
      </g>
    </svg>
  );
}

/** Small spot drawing for the closing call to action. */
export function DocsCleared() {
  return (
    <svg className="doodle art-float" viewBox="0 0 340 190" aria-hidden="true">
      <path className="stroke" d="M14 172 H326" />
      <path className="paper-fill" d="M60 62 H160 V150 H60 Z" />
      <path className="thin" d="M76 88 h58 M76 106 h44 M76 124 h58" />
      <path className="paper-fill" d="M186 46 H286 V150 H186 Z" />
      <path className="stroke" d="M206 100 l12 12 l26 -30" />
      <path className="thin" d="M202 62 h50 M202 76 h32" />
      <path className="thin scan" d="M166 96 h14 M166 82 h8 M166 110 h8" />
    </svg>
  );
}

/** Module card glyphs, keyed by the `icon` field in content.js. */
const glyphs = {
  face: (
    <>
      <rect className="stroke" x="8" y="10" width="48" height="40" rx="5" />
      <circle className="stroke" cx="32" cy="26" r="8" />
      <path className="stroke" d="M20 44 C20 34 44 34 44 44" />
      <path className="thin" d="M14 16 v-2 M50 16 v-2" />
    </>
  ),
  voice: <path className="stroke" d="M8 32 h6 l5 -14 l6 30 l6 -40 l6 44 l5 -22 l4 2 h10" />,
  shield: (
    <>
      <path className="stroke" d="M32 8 L52 16 v16 C52 44 42 52 32 56 C22 52 12 44 12 32 V16 Z" />
      <path className="stroke" d="M24 32 l6 6 l12 -13" />
    </>
  ),
  doc: (
    <>
      <path className="stroke" d="M16 8 h22 l12 12 v36 H16 Z" />
      <path className="stroke" d="M38 8 v12 h12" />
      <path className="thin" d="M24 32 h16 M24 42 h10" />
      <circle className="stroke" cx="44" cy="44" r="9" />
      <path className="stroke" d="M51 51 l6 6" />
    </>
  ),
  phone: (
    <>
      <path
        className="stroke"
        d="M14 20 C14 12 22 8 30 10 l6 12 l-7 5 C31 33 34 37 39 40 l5 -7 l12 6 C58 47 54 55 46 55 C28 55 14 38 14 20 Z"
      />
      <path className="thin" d="M44 12 c6 2 9 6 10 12" />
    </>
  ),
  form: (
    <>
      <rect className="stroke" x="10" y="14" width="44" height="36" rx="5" />
      <path className="thin" d="M18 26 h10 M34 26 h12 M18 36 h20 M44 36 h2" />
      <path className="stroke" d="M26 46 h12" />
    </>
  ),
};

export function ModuleIcon({ name }) {
  return (
    <svg className="micon doodle" viewBox="0 0 64 64" aria-hidden="true">
      {glyphs[name]}
    </svg>
  );
}

export function Tick() {
  return (
    <span className="tick">
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M4 12.5l5 5L20 6.5" />
      </svg>
    </span>
  );
}
