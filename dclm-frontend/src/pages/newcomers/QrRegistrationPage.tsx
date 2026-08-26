import { useNavigate } from 'react-router-dom';
import { QRCodeSVG } from 'qrcode.react';

export function QrRegistrationPage() {
  const navigate = useNavigate();
  const registrationUrl = `${window.location.origin}/register`;

  return (
    <>
      <div className="toolbar">
        <div className="tabs">
          <button className="tab" onClick={() => navigate('/newcomers')}>Pipeline</button>
          <button className="tab" onClick={() => navigate('/newcomers/follow-up')}>Follow-up</button>
          <button className="tab active">QR Registration</button>
          <button className="tab" onClick={() => navigate('/newcomers/manual')}>Manual Entry</button>
        </div>
      </div>
      <div className="card" style={{ maxWidth: 480, textAlign: 'center', margin: '0 auto' }}>
        <h3>Project this during the newcomer announcement</h3>
        <p className="muted">
          Newcomers scan this with their phone camera to fill the welcome form themselves. Submissions
          land directly in the New column, already tagged with source "Church website (QR self-registration)".
          This QR code is for Bahrain only. DCLM Bahrain is the main church; Qatar remains a supporting
          location for now.
        </p>
        <div style={{ margin: '16px auto', border: '1px solid var(--line)', borderRadius: 10, padding: 16, display: 'inline-block' }}>
          <QRCodeSVG value={registrationUrl} size={200} />
        </div>
        <div className="muted" style={{ fontSize: '.8rem', wordBreak: 'break-all' }}>{registrationUrl}</div>
      </div>
    </>
  );
}
