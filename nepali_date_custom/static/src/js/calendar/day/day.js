import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class Day extends Component {
  static template = "nepalidatepicker.dayCell";

  static props = {
    day: Object,
    onApply: Function,
  };
  setup() {}

  onClick(event) {
    this.props.onApply(this.props.day.date, this.props.day.ad_date);
  }
}

