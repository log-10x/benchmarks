// @loader: tenx

import {TenXObject, TenXCounter} from '@tenx/tenx'

export class FileObject extends TenXObject {

    constructor() {

        if (this.isObject) {
            TenXCounter.inc("fileObjects");
        }
    }
}
