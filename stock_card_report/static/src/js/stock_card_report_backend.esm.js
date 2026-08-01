import {Component, onMounted, onWillStart, useRef} from "@odoo/owl";
import {download} from "@web/core/network/download";
import {registry} from "@web/core/registry";
import {useService} from "@web/core/utils/hooks";

export class report_backend extends Component {
    static template = "report_stock_card_html";
    static props = ["*"];

    start() {
        this.pageRef.el.innerHTML = this.lines.html;
    }

    setup() {
        this.pageRef = useRef("page");
        onWillStart(async () => {
            this.lines = await this.orm.call("report.stock.card.report", "get_html", [
                this.context,
            ]);
        });
        onMounted(() => {
            this.start();
        });

        this.orm = useService("orm");

        const {active_id, active_model, context, ttype, url} =
            this.props.action.context;
        this.controllerUrl = url;

        this.context = context || {};
        Object.assign(this.context, {
            active_id: active_id || this.props.action.params.active_id,
            model: active_model || false,
            ttype: ttype || false,
        });
    }
    onClickPrint() {
        const data = JSON.stringify(this.lines.html);
        const url = this.controllerUrl
            .replace(":active_id", this.context.active_id)
            .replace(":active_model", this.context.model)
            .replace("output_format", "pdf");
        download({
            data: {data},
            url,
        });
    }
    onClickExport() {
        const data = JSON.stringify(this.lines.html);
        const url = this.controllerUrl
            .replace(":active_id", this.context.active_id)
            .replace(":active_model", this.context.model)
            .replace("output_format", "xlsx");
        download({
            data: {data},
            url,
        });
    }
}
registry.category("actions").add("stock_card_report_backend", report_backend);
