import { useCallback, useEffect, useRef, useState } from 'react';

/**
 * Face capture — upload a photo or take one with the camera.
 *
 * Assurance previously accepted uploads only, which is backwards for the thing
 * it is meant to demonstrate: an officer at a dealer counter is looking at the
 * applicant, not at a folder of files. Taking the photo live also removes the
 * most obvious way to feed the system a picture of someone else.
 *
 * The camera is a convenience, not a control. A photo taken here proves nothing
 * about presence on its own — that is LiveChallenge's job, and the assurance
 * weights say so. This component only makes the capture easier.
 */
export default function FaceCapture({ file, onPick, label = 'Face capture' }) {
  const fileRef = useRef(null);
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);

  const [mode, setMode] = useState('idle'); // idle | camera | denied
  const [preview, setPreview] = useState(null);

  const stop = useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
  }, []);

  useEffect(() => stop, [stop]);

  // Preview whatever is currently selected, however it was chosen.
  useEffect(() => {
    if (!file) return setPreview(null);
    const url = URL.createObjectURL(file);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  async function openCamera() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 640, height: 480, facingMode: 'user' },
      });
      streamRef.current = stream;
      setMode('camera');
      // The element only exists once mode flips, so attach on the next frame.
      requestAnimationFrame(() => {
        if (videoRef.current) videoRef.current.srcObject = stream;
      });
    } catch {
      setMode('denied');
    }
  }

  function closeCamera() {
    stop();
    setMode('idle');
  }

  function capture() {
    const v = videoRef.current;
    const c = canvasRef.current;
    if (!v || !c) return;
    c.width = v.videoWidth || 640;
    c.height = v.videoHeight || 480;
    c.getContext('2d').drawImage(v, 0, 0, c.width, c.height);
    c.toBlob(
      (blob) => {
        if (!blob) return;
        // Name it so the backend's extension sniffing behaves.
        const shot = new File([blob], `capture-${Date.now()}.jpg`, { type: 'image/jpeg' });
        onPick(shot);
        closeCamera();
      },
      'image/jpeg',
      0.92,
    );
  }

  return (
    <div className="field">
      <label>{label}</label>

      {mode === 'camera' ? (
        <div className="fc-camera">
          <video ref={videoRef} autoPlay playsInline muted className="fc-video" />
          <div className="row-actions">
            <button className="btn btn-primary btn-sm" type="button" onClick={capture}>
              Take photo
            </button>
            <button className="btn btn-ghost btn-sm" type="button" onClick={closeCamera}>
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <>
          {preview && (
            <div className="fc-preview">
              <img src={preview} alt="Selected face capture" />
              <span className="fc-name">
                {file?.name} · {(file.size / 1024).toFixed(0)} KB
              </span>
            </div>
          )}

          <div className="row-actions fc-actions">
            <button className="btn btn-ghost btn-sm" type="button" onClick={openCamera}>
              {preview ? 'Retake with camera' : 'Use camera'}
            </button>
            <button
              className="btn btn-ghost btn-sm"
              type="button"
              onClick={() => fileRef.current?.click()}
            >
              {preview ? 'Choose another file' : 'Upload a photo'}
            </button>
            {preview && (
              <button className="btn btn-ghost btn-sm" type="button" onClick={() => onPick(null)}>
                Clear
              </button>
            )}
          </div>

          {mode === 'denied' && (
            <p className="fc-denied">
              Camera unavailable — the browser refused access, or this page is not on a secure
              origin. Upload a photo instead.
            </p>
          )}
        </>
      )}

      <canvas ref={canvasRef} className="hidden" />
      <input
        ref={fileRef}
        type="file"
        accept="image/*"
        hidden
        onChange={(e) => onPick(e.target.files?.[0] ?? null)}
      />
    </div>
  );
}
