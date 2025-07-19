/* zha-lock-manager-card.js – 2025‑07‑19 patched */
import { LitElement, html, css } from "https://unpkg.com/lit-element?module";

class ZhaLockManagerCard extends LitElement {
  static get properties() {
    return { hass: {}, config: {}, _lock: {} };
  }

  setConfig(config) {
    this.config = { ...config };
    this._lock  = config.lock ?? undefined;   // undefined triggers auto‑discover
  }

  /** ---------- helpers ---------- */
  _discoverLocks() {
    // Sensors created by the integration end with "_codes"
    const sensors = Object.keys(this.hass.states).filter(
      (id) => id.startsWith("sensor.") && id.endsWith("_codes")
    );

    return sensors.map((s) => {
      const st  = this.hass.states[s];
      const fn  = st?.attributes?.friendly_name ?? "";
      const lockId = fn.replace(/ codes$/i, "");   // exact original entity id
      return { lockId, sensorId: s };
    });
  }

  /** ---------- rendering ---------- */
  render() {
    if (!this.hass) return html``;

    /* 1. Pick a lock */
    const locks = this._discoverLocks();
    if (!locks.length)
      return html`<ha-card><p>No ZHA Lock Manager sensors found</p></ha-card>`;

    if (!this._lock) this._lock = locks[0].lockId;

    const sensorId = `sensor.${this._lock.replace(/\./g, "_")}_codes`;
    const sensor   = this.hass.states[sensorId];

    // keep only numeric keys (slot numbers)
    const codes = sensor
      ? Object.entries(sensor.attributes).filter(([k]) => /^\d+$/.test(k))
      : [];

    return html`
      <ha-card header="ZHA Lock Codes">
        ${locks.length > 1
          ? html`
              <div class="row">
                <span>Lock:</span>
                <select @change=${(e) => (this._lock = e.target.value)}>
                  ${locks.map(
                    (l) =>
                      html`<option value=${l.lockId} ?selected=${l.lockId === this._lock}
                        >${l.lockId}</option
                      >`
                  )}
                </select>
              </div>
            `
          : null}

        <div class="codes">
          ${codes.length
            ? codes.map(
                ([slot, info]) => html`
                  <div class="code-row">
                    <span>Slot&nbsp;${slot}</span>
                    <span>${info.name || ""}</span>
                    <span>${info.code || ""}</span>
                    <mwc-button @click=${() => this._delete(slot)}>Delete</mwc-button>
                  </div>
                `
              )
            : html`<p>No codes found</p>`}
        </div>

        <mwc-button @click=${this._openAddDialog.bind(this)}>Add Code</mwc-button>
      </ha-card>
    `;
  }

  /** ---------- actions ---------- */
  async _delete(slot) {
    await this.hass.callService("zha_lock_manager", "delete_code", {
      lock_entity: this._lock,
      slot: Number(slot),
    });
  }

  async _openAddDialog() {
    const name = prompt("Name (optional):");
    const code = prompt("User Code:");
    if (!code) return;
    const temp = confirm("Is this a temporary code?");
    if (temp) {
      const mins = prompt("Duration in minutes:", "60");
      await this.hass.callService("zha_lock_manager", "create_temp_code", {
        lock_entity: this._lock,
        user_code: code,
        name,
        duration_minutes: Number(mins) || 60,
      });
    } else {
      await this.hass.callService("zha_lock_manager", "add_code", {
        lock_entity: this._lock,
        user_code: code,
        name,
      });
    }
  }

  /** ---------- styles ---------- */
  static get styles() {
    return css`
      ha-card {
        padding: 16px;
      }
      .row {
        display: flex;
        align-items: center;
        margin-bottom: 8px;
        gap: 8px;
      }
      .code-row {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 8px;
        padding: 4px 0;
      }
      .codes {
        margin-bottom: 16px;
      }
    `;
  }
}

customElements.define("zha-lock-manager-card", ZhaLockManagerCard);
