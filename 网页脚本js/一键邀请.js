(async function () {
  // 函数用于等待
  function wait(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  const moreBtnEle = document.querySelector(
    ".QuestionInvitation-content .QuestionMainAction.Button"
  );

  moreBtnEle?.click();

  wait(500);

  // 选择所有符合选择器的按钮
  const btnElements = document.querySelectorAll(
    ".Question-mainColumn .List .List-item .ContentItem-extra button"
  );

  let previousTimestamp = performance.now(); // 初始化为当前时间戳

  // 遍历按钮并依次点击
  for (let i = 0; i < btnElements.length; i++) {
    const btn = btnElements[i];
    const currentTimestamp = performance.now();

    // 计算和上一个按钮点击的时间差
    const timeDifference = currentTimestamp - previousTimestamp;

    // 输出时间差
    console.log(
      `按钮 ${i + 1} clicked, time since last click: ${timeDifference.toFixed(
        2
      )} ms`
    );

    // 点击按钮
    setTimeout(() => {
      btn.click();
      previousTimestamp = performance.now(); // 更新为当前时间戳
    }, 10 * i);
  }
})();
