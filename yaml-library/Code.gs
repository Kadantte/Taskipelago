const DRIVE_FOLDER_ID = '1-zjxfR_OHQD4OgOISBVcO6GXEZtm3-B7gUGFvkkLVSokfjBb7xtKvgoQrSk-sBrE1ycFzLgA';
const MAX_FILE_BYTES = 262144;
const NAME_PATTERN = /^[A-Za-z0-9-]+$/;
const VERSION_PATTERN = /^\d+\.\d+\.\d+$/;

function doGet() {
  return HtmlService.createHtmlOutputFromFile('Index')
    .setTitle('Taskipelago Community YAML Submission')
    .addMetaTag('viewport', 'width=device-width, initial-scale=1');
}

function submitYaml(slotName, authorName, version, base64Data, originalFileName) {
  slotName = (slotName || '').trim();
  authorName = (authorName || '').trim();
  version = (version || '').trim();

  if (!NAME_PATTERN.test(slotName)) {
    throw new Error('Slot name may only contain letters, numbers, and hyphens (no spaces or underscores).');
  }
  if (!NAME_PATTERN.test(authorName)) {
    throw new Error('Author name may only contain letters, numbers, and hyphens (no spaces or underscores).');
  }
  if (!VERSION_PATTERN.test(version)) {
    throw new Error('Version must look like 1.0.0');
  }
  if (!/\.ya?ml$/i.test(originalFileName || '')) {
    throw new Error('File must be a .yaml or .yml file.');
  }

  const bytes = Utilities.base64Decode(base64Data);
  if (bytes.length === 0) {
    throw new Error('Uploaded file is empty.');
  }
  if (bytes.length > MAX_FILE_BYTES) {
    throw new Error('File is too large (limit ' + Math.floor(MAX_FILE_BYTES / 1024) + ' KB).');
  }

  const text = Utilities.newBlob(bytes).getDataAsString('UTF-8');
  if (text.indexOf(':') === -1) {
    throw new Error('File does not look like valid YAML.');
  }

  const fileName = slotName + '_' + authorName + '_' + version.replace(/\./g, '-') + '.yaml';
  const folder = DriveApp.getFolderById(DRIVE_FOLDER_ID);

  const existing = folder.getFilesByName(fileName);
  while (existing.hasNext()) {
    existing.next().setTrashed(true);
  }

  const blob = Utilities.newBlob(bytes, 'application/x-yaml', fileName);
  folder.createFile(blob);

  return fileName;
}
