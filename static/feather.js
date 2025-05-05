import * as arrow from "https://cdn.jsdelivr.net/npm/apache-arrow@19.0.1/+esm";

async function fetchAndParseArrow() {
  const res = await fetch('/api/data.arrow');
  const buffer = await res.arrayBuffer();
  const table = arrow.tableFromIPC(new Uint8Array(buffer));

  const parsedData = [];

  for (let i = 0; i < table.numRows; i++) {
    const row = {};
    table.schema.fields.forEach((field, colIdx) => {
      const column = table.getChildAt(colIdx);
      row[field.name] = column.get(i);
    });
    parsedData.push(row);
  }

  console.log("Распарсенные строки:", parsedData);
}

fetchAndParseArrow();
