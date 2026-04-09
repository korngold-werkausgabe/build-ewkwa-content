xquery version "3.1";

declare namespace mei = "http://www.music-encoding.org/ns/mei";
declare namespace tei = "http://www.tei-c.org/ns/1.0";
declare namespace map = "http://www.w3.org/2005/xpath-functions/map";

(: ####################################### :)
(: External Parameters :)

declare variable $propertiesPath as xs:string external;
declare variable $csvPathsString as xs:string external;
declare variable $sourcesPath as xs:string external;
declare variable $editionSlug as xs:string external;
declare variable $volSlug as xs:string external;
declare variable $subGroups as xs:string external;
declare variable $groupsTitleDe as xs:string external;
declare variable $groupsTitleEn as xs:string external;

(: ####################################### :)

declare function local:buildConnection($editionMeasure, $csvHead, $fields, $sources, $editionBaseURI) {
  let $mdivN := tokenize($editionMeasure, '_')[1]
  let $connectionMeasureLabel := tokenize($editionMeasure, '_')[2]
  return
  <connection
    xmlns="http://www.edirom.de/ns/1.3"
    name="{$connectionMeasureLabel}"
    plist="{
        for $key at $pos in $csvHead
        let $value := $fields[$pos]
        (: sources - find by siglum in filename with pattern matching to get exact file :)
        (: Try to match edirom-source_{key}_ first (e.g., edirom-source_B_03.xml), then edirom-source_{key}.xml :)
        let $sourceDoc := (
          $sources/mei:mei[matches(base-uri(.), concat('edirom-source_', $key, '(_|\.xml)'))][1],
          $sources/mei:mei[contains(base-uri(.), concat('edirom-source_', $key))][1]
        )[1]
        let $sourceFileName := if ($sourceDoc) then tokenize(base-uri($sourceDoc), '/')[last()] else ''
        let $source := $sourceDoc[1]
        let $sourceValues :=
        if (contains($value, ';')) then
          tokenize($value, ';')
        else
          ($value)
        
        return
          if ($source) then
            (
            for $sourceValue in $sourceValues[string-length(normalize-space(.)) > 0]
            let $sourceMdivN := tokenize($sourceValue, '_')[1]
            let $sourceMeasureLabel := tokenize($sourceValue, '_')[2]
            return
              if (not(empty($sourceMeasureLabel))) then
                (
                if (exists($source[1]//mei:mdiv[@n = $sourceMdivN]//mei:measure[@label = $sourceMeasureLabel]/@xml:id)) then
                  (
                  let $measureID := $source[1]//mei:mdiv[@n = $sourceMdivN]//mei:measure[@label = $sourceMeasureLabel]/@xml:id
                  return
                    if (count($measureID) > 1) then
                      (
                      for $measure in $measureID
                      return
                        $editionBaseURI || $sourceFileName || '#' || string($measure) || ' '
                      )
                    else
                      (
                      $editionBaseURI || $sourceFileName || '#' || string($measureID) || ' '
                      )
                  )
                else
                  ()
                )
              else
                ()
            )
          else
            ()
      
      }"/>
};

(: ####################################### :)
(: Variables :)

(: Parse JSON structure from csvPathsString :)
let $csvData := if ($csvPathsString != '') then parse-json($csvPathsString) else ()
let $sources := collection($sourcesPath)

let $editionBaseURI := 'xmldb:exist:///db/apps/edirom-content/' || $volSlug || '/' || $editionSlug || '/sources/'

(: ####################################### :)
return
  <concordance
    xmlns="http://www.edirom.de/ns/1.3"
    name='concMain'>
    <names>
      <name
        xml:lang='de'>Edition</name>
      <name
        xml:lang='en'>Edition</name>
    </names>
    <groups>
      <names>
        <name xml:lang='de'>{$groupsTitleDe}</name>
        <name xml:lang='en'>{$groupsTitleEn}</name>
      </names>
      {
        for $csvEntry in $csvData?*
        return
          try {
            let $csvText := fn:unparsed-text(string($csvEntry?file))
            let $csvLines := tokenize($csvText, '\n')
            let $csvHead := tokenize($csvLines[1], ',')
            let $csvBody := remove($csvLines, 1)
            return
              <group name='{$csvEntry?title_de}'>
                <names>
                  <name xml:lang='de'>{$csvEntry?title_de}</name>
                  <name xml:lang='en'>{$csvEntry?title_en}</name>
                </names>
                <connections label="Takt">
                  <labels>
                    <label xml:lang="de">Takt</label>
                    <label xml:lang="en">Measure</label>
                  </labels>
                  {
                    for $line in $csvBody[string-length(normalize-space(.)) > 0]
                    let $fields := tokenize($line, ',')
                    let $editionMeasure := $fields[1]
                    return
                      if (normalize-space($editionMeasure)) then
                        local:buildConnection($editionMeasure, $csvHead, $fields, $sources, $editionBaseURI)
                      else
                        ()
                  }
                </connections>
              </group>
          }
          catch * {
            error(
              xs:QName("local:csv-error"),
              concat("CSV file could not be loaded from ", $csvEntry?file, ". Error: ", $err:code, " - ", $err:description)
            )
          }
      }
    </groups>
  </concordance>