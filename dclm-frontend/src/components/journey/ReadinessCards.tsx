import { Icon } from '../ui/Icon';
import type { Readiness } from '../../api/newcomers';

/**
 * Why someone is, or is not, proposed for membership.
 *
 * Shows the working rather than a verdict. A bare "not ready" invites
 * exactly the question these cards answer, and an administrator deciding
 * about a person deserves to see what the decision rests on.
 */
function Ring({ percent, colour }: { percent: number; colour: string }) {
  const r = 24;
  const circ = 2 * Math.PI * r;
  const on = Math.max(0, Math.min(100, percent)) / 100 * circ;
  return (
    <svg width="56" height="56" viewBox="0 0 56 56" aria-hidden="true">
      <circle cx="28" cy="28" r={r} fill="none" stroke="var(--line)" strokeWidth="6" />
      <circle cx="28" cy="28" r={r} fill="none" stroke={colour} strokeWidth="6"
        strokeLinecap="round" strokeDasharray={`${on} ${circ}`}
        transform="rotate(-90 28 28)" />
    </svg>
  );
}

function Foot({ met, metText, notText }: { met: boolean; metText: string; notText: string }) {
  return (
    <div className={`rc-foot${met ? ' ok' : ''}`}>
      <Icon name={met ? 'check' : 'alert'} size={14} />
      {met ? metText : notText}
    </div>
  );
}

export function ReadinessCards({ r }: { r: Readiness }) {
  const GREEN = 'var(--green)';
  const AMBER = 'var(--amber)';
  const BLUE = 'var(--blue)';
  const monthsLeft = Math.max(0, r.window_months - r.months_attending);

  return (
    <div className="readycards">
      <div className="rc">
        <div className="rc-head"><span>Friday attendance</span><Icon name="calendar" size={16} /></div>
        <div className="rc-body">
          <Ring percent={r.attendance_percent} colour={r.attendance_met ? GREEN : AMBER} />
          <div>
            <div className="rc-value">{r.attendance_percent}%</div>
            <div className="rc-sub">{r.services_attended} of {r.services_held} services</div>
          </div>
        </div>
        <Foot met={r.attendance_met}
          metText={`Above the ${r.min_percent}% needed`}
          notText={`Needs ${r.min_percent}%`} />
      </div>

      <div className="rc">
        <div className="rc-head"><span>Salvation</span><Icon name="check" size={16} /></div>
        <div className="rc-body">
          <div className={`rc-badge ${r.has_salvation ? 'yes' : 'no'}`}>
            <Icon name={r.has_salvation ? 'check' : 'alert'} size={r.has_salvation ? 26 : 24} />
          </div>
          <div>
            <div className={`rc-value${r.has_salvation ? '' : ' muted'}`}>
              {r.has_salvation ? 'Yes' : 'Not yet'}
            </div>
            <div className="rc-sub">{r.has_salvation ? 'Milestone recorded' : 'No milestone'}</div>
          </div>
        </div>
        <Foot met={r.has_salvation} metText="Milestone met" notText="Record it on the profile" />
      </div>

      <div className="rc">
        <div className="rc-head"><span>Time attending</span><Icon name="alert" size={16} /></div>
        <div className="rc-body">
          <Ring percent={(r.months_attending / r.window_months) * 100}
            colour={r.time_met ? GREEN : BLUE} />
          <div>
            <div className="rc-value">{r.months_attending} mo</div>
            <div className="rc-sub">
              {r.first_attended ? `since ${r.first_attended}` : 'not yet attended'}
            </div>
          </div>
        </div>
        <Foot met={r.time_met}
          metText={`Full ${r.window_months} months`}
          notText={`${monthsLeft} month${monthsLeft === 1 ? '' : 's'} to go`} />
      </div>
    </div>
  );
}
