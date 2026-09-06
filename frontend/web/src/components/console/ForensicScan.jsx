import { useEffect, useRef, useState } from 'react';

/**
 * Forensic scan view.
 *
 * Shows the uploaded face while the calibrated pipeline runs: a sweeping scan
 * line, a detection box that locks onto the face MTCNN actually found, and the
 * pipeline stages resolving one after another.
 *
 * Two rules this component follows, because it is shown to an audience:
 *
 *   1. It never invents a result. The stage list advances on a timer only up to
 *      the point the real response arrives; the verdict itself is always the
 *      backend's. If the request fails, the sequence stops and says so.
 *   2. The detection box is drawn from the real bounding box in the response,
 *      scaled to the rendered image — not a decorative rectangle in the middle.
 */

const STAGES = [
  { id: 'load', label: 'Reading image', detail: 'Decoding and normalising to RGB' },
  { id: 'detect', label: 'Locating face', detail: 'MTCNN detection, largest subject' },
  { id: 'crop', label: 'Cropping to face', detail: 'Matching the training distribution' },
  { id: 'freq', label: 'Frequency analysis', detail: 'FFT, block-DCT and Haar wavelet sub-bands' },
  { id: 'primary', label: 'Forensic classifier', detail: 'Calibrated model over 34 features' },
  { id: 'context', label: 'Bias context check', detail: 'Screening for the known failure mode' },
  { id: 'fuse', label: 'Applying gates', detail: 'Capture-quality floor, then decide' },
];

export default function ForensicScan({ file, result, running, error }) {
  const [preview, setPreview] = useState(null);
  const [stage, setStage] = useState(-1);
  const imgRef = useRef(null);
  const [box, setBox] = useState(null);

  // Object URL for the uploaded file, revoked on change to avoid a leak.
  useEffect(() => {
    if (!file) return setPreview(null);
    const url = URL.createObjectURL(file);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  // Advance the stage list while the request is in flight. It deliberately
  // stops at the last stage rather than completing on its own — completion is
  // driven by the real response arriving.
  useEffect(() => {
    if (!running) return undefined;
    setStage(0);
    const timer = setInterval(() => {
      setStage((s) => (s >= STAGES.length - 1 ? s : s + 1));
    }, 620);
    return () => clearInterval(timer);
  }, [running]);

  useEffect(() => {
    if (result) setStage(STAGES.length);
    if (error) setStage(-1);
  }, [result, error]);

  // Map the real bounding box onto the rendered image size.
  useEffect(() => {
    const det = result?.stages?.face_detection;
    const el = imgRef.current;
    if (!det?.found || !det.box || !det.image_size || !el) return setBox(null);
    const [nw, nh] = det.image_size;
    const scaleX = el.clientWidth / nw;
    const scaleY = el.clientHeight / nh;
    const [x, y, w, h] = det.box;
    setBox({
      left: x * scaleX,
      top: y * scaleY,
      width: w * scaleX,
      height: h * scaleY,
    });
  }, [result, preview]);

  if (!preview) {
    return <div className="empty">Select a face image to run the forensic pipeline.</div>;
  }

  const det = result?.stages?.face_detection;

  return (
    <div className="scan-wrap">
      <div className={`scan-stage ${running ? 'is-scanning' : ''}`}>
        <img ref={imgRef} src={preview} alt="Uploaded face under analysis" className="scan-img" />

        {running && <div className="scan-line" />}
        {running && <div className="scan-grid" />}

        {box && (
          <div className="scan-box" style={box}>
            <span className="scan-corner tl" />
            <span className="scan-corner tr" />
            <span className="scan-corner bl" />
            <span className="scan-corner br" />
            {det?.confidence != null && (
              <span className="scan-box-label">face {(det.confidence * 100).toFixed(1)}%</span>
            )}
          </div>
        )}

        {result && !det?.found && (
          <div className="scan-noface">No face detected — full frame scored</div>
        )}
      </div>

      <ol className="scan-stages">
        {STAGES.map((s, i) => {
          const state =
            error && i === stage + 1 ? 'failed'
            : i < stage ? 'done'
            : i === stage && running ? 'active'
            : stage >= STAGES.length ? 'done'
            : 'pending';
          return (
            <li key={s.id} className={`scan-step scan-${state}`}>
              <span className="scan-dot">
                {state === 'done' ? '✓' : state === 'failed' ? '!' : i + 1}
              </span>
              <span className="scan-text">
                <b>{s.label}</b>
                <em>{s.detail}</em>
              </span>
            </li>
          );
        })}
      </ol>

      {error && <div className="notice notice-bad">{error}</div>}
    </div>
  );
}
