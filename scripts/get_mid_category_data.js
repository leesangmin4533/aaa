
(function() {
    try {
        const app = window.nexacro.getApplication();
        const dsList = app.mainframe.HFrameSet00.VFrameSet00.FrameSet.STMB011_M0.form.div_workForm.form.dsList;

        if (!dsList) {
            return {
                error: "Dataset 'dsList' not found at the specified path."
            };
        }

        const rowCount = dsList.getRowCount();
        const data = [];

        for (let i = 0; i < rowCount; i++) {
            data.push({
                "MID_CD": dsList.getColumn(i, "MID_CD"),
                "MID_NM": dsList.getColumn(i, "MID_NM")
            });
        }

        return {
            data: data
        };
    } catch (e) {
        return {
            error: e.toString()
        };
    }
})();
