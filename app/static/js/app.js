/*
教学用脚本（View 静态资源）

目标：
- 演示 JS 从模板抽离到 static/js
- 提供一个可见的小交互：页面加载后自动聚焦第一个输入框
*/

window.addEventListener("DOMContentLoaded", () => {
  const firstInput = document.querySelector("input");
  if (firstInput) firstInput.focus();
});
