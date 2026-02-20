/** @odoo-module **/

import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";
import { session } from "@web/session";
import { useService } from "@web/core/utils/hooks";
import { Component, xml } from "@odoo/owl";

export class LoginWarningService extends Component {
    static template = xml`<div class="login_restriction_service" style="display:none;"/>`;

    setup() {
        try {
            // Use direct environment access to avoid proxying issues with useService in some Odoo environments
            this.rpc = this.env.services.rpc;
            this.notification = this.env.services.notification;
            this.userService = this.env.services.user;
            this.busService = this.env.services.bus_service;

            if (this.busService) {
                const handleNotification = (notifications) => {
                    for (const { type } of notifications) {
                        if (type === "login_restriction_logout") {
                            browser.location.reload();
                        }
                    }
                };

                // Odoo 17 Bus Service supports both EventTarget (addEventListener) and subscribe
                if (typeof this.busService.subscribe === 'function') {
                    this.busService.subscribe("notification", handleNotification);
                } else if (typeof this.busService.addEventListener === 'function') {
                    this.busService.addEventListener("notification", ({ detail }) => handleNotification(detail));
                }
            }

            this.startLogic();
        } catch (error) {
            console.error("LoginWarningService failed to initialize gracefully:", error);
        }
    }

    async startLogic() {
        try {
            // Only non-admins need the warning
            const isAdmin = await this.userService.hasGroup("base.group_system");
            if (isAdmin) {
                return;
            }

            // Get current company ID safely
            const companyId = session.company_id || (session.user_companies && session.user_companies.current_company[0]);
            if (!companyId) {
                return;
            }

            // Fetch company hours
            const companyData = await this.rpc("/web/dataset/call_kw/res.company/read", {
                model: 'res.company',
                method: 'read',
                args: [[companyId], ['restrict_login_start_hour', 'restrict_login_end_hour']],
                kwargs: {},
            });

            if (companyData && companyData.length > 0) {
                this.startHour = companyData[0].restrict_login_start_hour;
                this.endHour = companyData[0].restrict_login_end_hour;
                this.startCheckInterval();
            }
        } catch (error) {
            console.error("Login Warning Service crashed but prevented white screen:", error);
        }
    }

    startCheckInterval() {
        // Check for 5-minute warning every 1 minute (for better UX)
        this.warningInterval = browser.setInterval(() => {
            this.checkTime(true); // warningOnly = true
        }, 60000);

        // Forced session validation every 5 minutes (Modification #2)
        this.forceCheckInterval = browser.setInterval(() => {
            this.checkTime(false); // warningOnly = false (allow reload)
        }, 300000); // 5 minutes

        // Also check once immediately
        this.checkTime(false);
    }

    checkTime(warningOnly = false) {
        try {
            const now = new Date();
            // Convert to Morocco Time
            const moroccoTimeStr = now.toLocaleString("en-US", { timeZone: "Africa/Casablanca", hour12: false });

            // Handle different locale string formats
            const timePart = moroccoTimeStr.includes(', ') ? moroccoTimeStr.split(', ')[1] : moroccoTimeStr.split(' ')[1];
            if (!timePart) return;

            const [h, m] = timePart.split(':').map(Number);
            const currentHour = h + m / 60.0;

            // 5 minutes before endHour
            const warningTime = this.endHour - (5 / 60.0);

            if (currentHour >= this.endHour) {
                if (!warningOnly) {
                    // Force logout by reloading (ir_http will catch it)
                    browser.location.reload();
                }
            } else if (currentHour >= warningTime && !this.warningShown) {
                this.notification.add(
                    "Warning: Working hours are ending soon. Please save your work.",
                    {
                        title: "Access Restriction",
                        type: "warning",
                        sticky: true,
                    }
                );
                this.warningShown = true;
            } else if (currentHour < warningTime) {
                this.warningShown = false;
            }
        } catch (e) {
            console.error("Login Warning check failed:", e);
        }
    }
}

// Register as a main component
registry.category("main_components").add("LoginWarningService", {
    Component: LoginWarningService,
});
