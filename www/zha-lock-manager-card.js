
import { LitElement, html, css } from "https://unpkg.com/lit-element?module";

class ZhaLockManagerCard extends LitElement {
  static get properties() {
    return { hass: {}, config: {} };
  }

  setConfig(config) {
    if (!config.lock) {
      throw new Error("Missing 'lock' property in card config");
    }
    this.config = config;
  }

  render() {
    if (!this.hass) return html``;
    const lockId = this.config.lock;
    const sensorId = `sensor.${lockId.replace('.', '_')}_codes`;
    const sensor = this.hass.states[sensorId];
    const codes = sensor ? Object.entries(sensor.attributes) : [];

    return html`
      <ha-card header="ZHA Lock Codes">
        <div class="codes">
          ${
            codes.length
              ? codes.map(
                  ([slot, info]) => html`
                    <div class="code-row">
                      <span>Slot ${slot}</span>
                      <span>${info.name || ""}</span>
                      <span>${info.code}</span>
                      <mwc-button @click=${() => this._delete(slot)}>Delete</mwc-button>
                    </div>
                  `
                )
              : html`<p>No codes found</p>`
          }
        </div>
        <mwc-button @click=${this._openAddDialog.bind(this)}>Add Code</mwc-button>
      </ha-card>
    `;
  }

  async _delete(slot) {
    await this.hass.callService("zha_lock_manager", "delete_code", {
      lock_entity: this.config.lock,
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
        lock_entity: this.config.lock,
        user_code: code,
        name,
        duration_minutes: Number(mins) || 60,
      });
    } else {
      await this.hass.callService("zha_lock_manager", "add_code", {
        lock_entity: this.config.lock,
        user_code: code,
        name,
      });
    }
  }

  static get styles() {
    return css`
      ha-card {
        padding: 16px;
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
