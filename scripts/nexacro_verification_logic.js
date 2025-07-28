(() => {
  // Nexacro 핵심 헬퍼 함수들을 window.automation에서 가져옵니다.
  const delay = window.automation.delay;

  async function verifyMidSaleQty(midCodeInfo) {
    try {
      if (!window.automation.parsedData) {
        console.warn("수집된 데이터(window.automation.parsedData)가 없습니다. 검증을 건너뜁니다.");
        return false;
      }

      const midCode = midCodeInfo.code;
      const midName = midCodeInfo.name;
      const expectedQty = midCodeInfo.expectedQuantity;

      console.log(`▶ 중분류 [${midCode} - ${midName}] 검증 시작, 기준 수량: ${expectedQty}`);

      let actualQty = 0;
      const productsForMidCode = window.automation.parsedData.filter(p => p.midCode === midCode);
      for (const p of productsForMidCode) {
        actualQty += p.sales;
      }

      if (expectedQty === actualQty) {
        console.log(`✅ [${midCode}] 수량 일치 → 기준 ${expectedQty} == 합계 ${actualQty}`);
        return true;
      } else {
        console.warn(`❌ [${midCode}] 수량 불일치! → 기준 ${expectedQty} ≠ 합계 ${actualQty}`);
        return false;
      }
    } catch (e) {
      console.error(`[verifyMidSaleQty] 검증 중 오류 발생 (midCode: ${midCodeInfo?.code || 'N/A'}):`, e.message);
      return false;
    }
  }

  async function runSaleQtyVerification() {
      console.log("===== 중분류-상품 수량 합계 검증 시작 =====");
      const midCodesSnapshot = window.automation.midCodesSnapshot;
      if (!midCodesSnapshot || midCodesSnapshot.length === 0) {
          console.error("수집된 중분류 스냅샷 데이터(window.automation.midCodesSnapshot)가 없습니다. 검증을 중단합니다.");
          return { success: false, failed_codes: ["midCodesSnapshot not found"] };
      }

      const failed_codes = [];
      for (const midCodeInfo of midCodesSnapshot) {
          const isSuccess = await verifyMidSaleQty(midCodeInfo);
          if (!isSuccess) {
              failed_codes.push(midCodeInfo.code);
          }
      }

      console.log("===== 모든 중분류 검증 완료 =====");
      if (failed_codes.length > 0) {
          return { success: false, failed_codes: failed_codes };
      } else {
          return { success: true, failed_codes: [] };
      }
  }

  // window.automation 객체에 검증 함수들 노출
  Object.assign(window.automation, {
    verifyMidSaleQty,
    runSaleQtyVerification,
  });
})();