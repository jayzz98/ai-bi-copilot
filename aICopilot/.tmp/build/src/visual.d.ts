import powerbi from "powerbi-visuals-api";
import "./../style/visual.less";
export declare class Visual implements powerbi.extensibility.visual.IVisual {
    private container;
    constructor(options: powerbi.extensibility.visual.VisualConstructorOptions);
    private currentData;
    update(options: powerbi.extensibility.visual.VisualUpdateOptions): void;
    private handleAsk;
}
