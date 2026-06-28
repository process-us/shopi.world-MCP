import fs from "fs";
import path from "path";

/**
 * Write one file from read_live_theme_mirror_files response.
 * @param {string} root - output directory
 * @param {{ filename: string, encoding: 'text'|'base64', content: string }} file
 */
export function writeMirrorFile(root, file) {
  const dest = path.join(root, file.filename);
  fs.mkdirSync(path.dirname(dest), { recursive: true });
  if (file.encoding === "text") {
    fs.writeFileSync(dest, file.content, "utf8");
  } else {
    fs.writeFileSync(dest, Buffer.from(file.content, "base64"));
  }
}
