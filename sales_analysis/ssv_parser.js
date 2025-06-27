function parseSSV(ssvText) {
  const lines = ssvText.split('\u001e');
  const datasetLine = lines.find(line => line.startsWith('Dataset:'));
  const datasetName = datasetLine ? datasetLine.split(':')[1] : undefined;

  const columnsLine = lines.find(line => line.includes('\u001fITEM_CD'));
  const colNames = columnsLine.split('\u001f').slice(1).map(col => col.split(':')[0]);

  const dataLines = lines.filter(line => line.startsWith('N\u001f'));
  const parsed = dataLines.map(row => {
    const values = row.split('\u001f').slice(1);
    const obj = {};
    colNames.forEach((key, i) => {
      obj[key] = values[i] || '';
    });
    return obj;
  });

  return { dataset: datasetName, rows: parsed };
}

module.exports = { parseSSV };

if (require.main === module) {
  const fs = require('fs');

  if (process.argv.length < 4) {
    console.error('Usage: node ssv_parser.js <config.json> <ssv_file>');
    process.exit(1);
  }

  const cfg = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
  const ssvText = fs.readFileSync(process.argv[3], 'utf8');
  const { dataset, rows } = parseSSV(ssvText);

  if (cfg.target_dataset && dataset !== cfg.target_dataset) {
    console.error(`Expected dataset ${cfg.target_dataset} but got ${dataset}`);
  }

  const filtered = rows.filter(row => {
    return Object.entries(cfg.filters || {}).every(([key, val]) => row[key] === val);
  });

  const output = filtered.map(row => {
    const obj = {};
    (cfg.output_fields || Object.keys(row)).forEach(k => {
      obj[k] = row[k];
    });
    return obj;
  });

  console.log(JSON.stringify(output, null, 2));
}
