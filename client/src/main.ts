import "./style.css";

function element<T extends HTMLElement>(selector: string): T {
  const found = document.querySelector<T>(selector);
  if (!found) {
    throw new Error("Missing element " + selector);
  }
  return found;
}

const connectButton = element<HTMLButtonElement>("#connect");
const statusText = element<HTMLSpanElement>("#status");

console.log("elements", connectButton, statusText);
