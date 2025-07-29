if (!window.automation) {
  window.automation = {};
}

// 헬퍼 함수 네임스페이스
window.automationHelpers = {
  originalTransaction: null,
  isHooked: false,
  targetDate: null,

  /**
   * Nexacro의 transaction 함수를 후킹하여 SSV 데이터를 조작합니다.
   * @param {string} targetSvcID - 조작할 서비스 ID (예: "search")
   */
  hookTransaction(targetSvcID) {
    if (this.isHooked) return; // 이미 후킹되어 있으면 중복 실행 방지

    const app = window.nexacro.getApplication();
    if (!app || typeof app.transaction !== 'function') {
      console.error("Nexacro transaction 함수를 찾을 수 없습니다.");
      return;
    }

    this.originalTransaction = app.transaction;
    const self = this;

    app.transaction = function(strSvcID, strURL, strInDatasets, strOutDatasets, strArgument, strCallbackFunc, bAsync, nDataType, bCompress) {
      console.log(`[HOOK_CALL] Original transaction called: svcID=${strSvcID}, strArgument=${strArgument}`);
      let modifiedArgument = strArgument;
      
      // 목표 서비스 ID와 일치하고, 조작할 날짜가 설정된 경우
      if (strSvcID.startsWith(targetSvcID) && self.targetDate) {
        console.log(`[HOOK_MODIFY] Target svcID '${strSvcID}' matched. Attempting to change strYmd to '${self.targetDate}'.`);
        modifiedArgument = self.updateSsv(strArgument, 'strYmd', self.targetDate);
        console.log(`[HOOK_MODIFY] Modified argument: ${modifiedArgument}`);
      }

      // 원본 transaction 함수 호출
      return self.originalTransaction.apply(this, [
        strSvcID, strURL, strInDatasets, strOutDatasets, 
        modifiedArgument, strCallbackFunc, bAsync, nDataType, bCompress
      ]);
    };

    this.isHooked = true;
    console.log("[HOOK] Nexacro transaction 함수가 활성화되었습니다.");
  },

  /**
   * 후킹된 transaction 함수를 원본으로 복원합니다.
   */
  unhookTransaction() {
    if (!this.isHooked || !this.originalTransaction) return;

    const app = window.nexacro.getApplication();
    if (app) {
      app.transaction = this.originalTransaction;
    }
    this.isHooked = false;
    this.originalTransaction = null;
    this.targetDate = null;
    console.log("[HOOK] Nexacro transaction 함수가 비활성화되었습니다.");
  },

  /**
   * SSV(String-Separated Values) 형식의 문자열에서 특정 키의 값을 변경합니다.
   * @param {string} ssv - 원본 SSV 문자열
   * @param {string} key - 변경할 키
   * @param {string} value - 새로운 값
   * @returns {string} 수정된 SSV 문자열
   */
  updateSsv(ssv, key, value) {
    const k = `${key}=`;
    if (ssv.includes(k)) {
      // 정규식을 사용하여 키=값 쌍을 교체
      const regex = new RegExp(`${key}=[^ ]*`);
      return ssv.replace(regex, `${key}=${value}`);
    } else {
      // 키가 없으면 새로 추가
      return ssv ? `${ssv} ${key}=${value}` : `${key}=${value}`;
    }
  },

  /**
   * 조작할 목표 날짜를 설정합니다.
   * @param {string} dateStr - YYYYMMDD 형식의 날짜
   */
  setTargetDate(dateStr) {
    this.targetDate = dateStr;
  }
};