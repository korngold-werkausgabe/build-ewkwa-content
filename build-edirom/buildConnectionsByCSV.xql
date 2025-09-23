xquery version "3.1";

declare namespace mei = "http://www.music-encoding.org/ns/mei";
declare namespace tei = "http://www.tei-c.org/ns/1.0";
declare namespace map = "http://www.w3.org/2005/xpath-functions/map";

(: ####################################### :)
(: Functions :)

declare function local:buildConnection($editionMeasure, $csvHead, $fields, $sources, $editionBaseURI) {
  <connection
    name="{$editionMeasure}"
    plist="{
        for $key at $pos in $csvHead
        let $value := $fields[$pos]
        (: sources :)
        let $source := $sources/mei:mei[descendant::mei:identifier[@type = 'siglum' and text() = $key]]
        let $sourceID := $source/@xml:id
        let $mdivN := tokenize($value, '_')[1]
        let $measureLabel :=
        if (contains($value, ';')) then
          (
          for $entry in tokenize($value, ';')
          return
            tokenize($entry, '_')[2]
          )
        else
          (
          tokenize($value, "_")[2]
          )
        
        return
          if (not(empty($measureLabel))) then
            (
            if (count($measureLabel) > 1) then
              (
              for $label in $measureLabel
              let $measureID := $source//mei:mdiv[@n = $mdivN]//mei:measure[@label = $label]/@xml:id
                where exists($measureID)
              return
                if (count($measureID) > 1) then
                  (
                  for $measure in $measureID
                  return
                    $editionBaseURI || $sourceID || '.xml#' || $measure || ' '
                  )
                else
                  (
                  $editionBaseURI || $sourceID || '.xml#' || $measureID || ' '
                  )
              )
            else
              (
              if (exists($source//mei:mdiv[@n = $mdivN]//mei:measure[@label = $measureLabel]/@xml:id)) then
                (
                let $measureID := $source//mei:mdiv[@n = $mdivN]//mei:measure[@label = $measureLabel]/@xml:id
                let $uri := if (count($measureID) > 1) then
                  (
                  for $measure in $measureID
                  return
                    $editionBaseURI || $sourceID || '.xml#' || $measure || ' '
                  )
                else
                  (
                  $editionBaseURI || $sourceID || '.xml#' || $measureID || ' '
                  )
                return
                  $uri
                )
              else
                ()
              )
            )
          else
            ()
      
      }"/>
};

(: ####################################### :)
(: Variables :)

let $properties-file := try{doc('../properties.xml')}catch* {error(
                  xs:QName('local:csv-error'),
                  'Properties file could not be loaded from "' || '../properties.xml' || '". Error: ' || $err:code || ' - ' || $err:description
                  )}
let $properties := $properties-file//property
let $uuids := $properties-file//uuids

(:  ID of Edirom edition file. :)
let $editionID := $uuids[@name = 'edition']
(:  ID of MEI work file. :)
let $workID := $uuids[@name = 'work']

(: Documents :)
let $inputCSV := './Konkordanz/edition.csv'
let $sources := collection('../Quellen/?select=*.xml')

let $editionBaseURI := 'xmldb:exist:///db/apps/edirom-content/' || $properties[@name = 'editionHandle']/text() || '/sources/'

(: ####################################### :)
return
  <concordance
    name='concMain'>
    <names>
      <name
        xml:lang='de'>Edition</name>
      <name
        xml:lang='en'>Edition</name>
    </names>
    <groups>
      <names>
        <name
          xml:lang='de'>{$properties[@name = 'mdivs']/label[@xml:lang = 'de']}</name>
        <name
          xml:lang='en'>{$properties[@name = 'mdivs']/label[@xml:lang = 'en']}</name>
      </names>
      {
        for $mdiv in $properties[@name = 'mdivs']//mdiv
        return
          <group
            n='{$mdiv/@n}'>
            <names>
              <name
                xml:lang='de'>{$mdiv/title/text()} – {$mdiv/subtitle/text()}</name>
              <name
                xml:lang='en'>{$mdiv/title/text()} – {$mdiv/subtitle/text()}</name>
            </names>
            <connections>{
                (: If the CSV file exists use csv mode :)
                try {
                  (: CSV handeling :)
                  let $csvText := fn:unparsed-text($inputCSV)
                  let $csvLines := tokenize($csvText, '\n')
                  let $csvHead := tokenize($csvLines[1], ',')
                  let $csvBody := remove($csvLines, 1)
                  
                  for $line in $csvBody
                  let $fields := tokenize($line, ',')
                  
                  let $mdivN := tokenize($fields[1], '_')[1]
                  let $editionMeasure := tokenize($fields[1], '_')[2]
                  return
                    if ($mdivN = $mdiv/@n) then
                      (local:buildConnection($editionMeasure, $csvHead, $fields, $sources, $editionBaseURI))
                    else
                      ()
                }
                catch * {
                  error(
                  xs:QName('local:csv-error'),
                  'CSV file could not be loaded from "' || $inputCSV || '". Error: ' || $err:code || ' - ' || $err:description
                  )
                }
              }
            </connections>
          </group>
      }
    </groups>
  </concordance>