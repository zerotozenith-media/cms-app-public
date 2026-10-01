import { useNavigate } from 'react-router-dom';
import { QRCodeSVG } from 'qrcode.react';

import { useState } from 'react';
import { useMyLocations } from '../../api/locations';
export function QrRegistrationPage() {
  const navigate = useNavigate();
  // One code per location, so a visitor lands in the pipeline of the
  // location they attended rather than always the main one.
  const { data: locations } = useMyLocations();
  const [chosen, setChosen] = useState('');
  const main = locations?.find((l) => l.is_core) ?? locations?.[0];
  const location = locations?.find((l) => l.id === chosen) ?? main;
  const registrationUrl = `${window.location.origin}/register${location ? `?location=${location.id}` : ''}`;

  return (
    <>
      <div className="toolbar">
        <div className="tabs">
          <button className="tab" onClick={() => navigate('/newcomers')}>Pipeline</button>
          <button className="tab" onClick={() => navigate('/newcomers/follow-up')}>Follow-up</button>
          <button className="tab" onClick={() => navigate('/newcomers/messages')}>Messages</button>
          <button className="tab active">QR Registration</button>
          <button className="tab" onClick={() => navigate('/newcomers/manual')}>Manual Entry</button>
        </div>
      </div>
      <div className="card" style={{ maxWidth: 480, textAlign: 'center', margin: '0 auto' }}>
        <h3>Project this during the newcomer announcement</h3>
        <p className="muted">
          Newcomers scan this with their phone camera to fill in the welcome form themselves. Each
          submission lands in the New column of the location this code is for, tagged with the source
          "Church website (QR self-registration)".
        </p>
        {(locations ?? []).length > 1 && (
          <div className="field" style={{ maxWidth: 260, margin: '0 auto', textAlign: 'left' }}>
            <label htmlFor="qr-location">Code for</label>
            <select id="qr-location" value={location?.id ?? ''} onChange={(e) => setChosen(e.target.value)}>
              {(locations ?? []).map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}
            </select>
          </div>
        )}
        {location && <div style={{ fontWeight: 700, marginTop: 10 }}>For visitors at {location.name}</div>}
        <div style={{ margin: '16px auto', border: '1px solid var(--line)', borderRadius: 10, padding: 16, display: 'inline-block' }}>
          <QRCodeSVG value={registrationUrl} size={200} />
        </div>
        <div className="muted" style={{ fontSize: '.8rem', wordBreak: 'break-all' }}>{registrationUrl}</div>
      </div>
    </>
  );
}
