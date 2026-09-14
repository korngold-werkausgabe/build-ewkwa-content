xquery version "3.1";

declare namespace mei = "http://www.music-encoding.org/ns/mei";
declare namespace tei = "http://www.tei-c.org/ns/1.0";
declare namespace map = "http://www.w3.org/2005/xpath-functions/map";

(: ####################################### :)
(: External Parameters :)

declare variable $concIds as xs:string external;
declare variable $concPath as xs:string external;
declare variable $subDiv as xs:string external;
declare variable $volSlug as xs:string external;

(: ####################################### :)

let $editionBaseURI := 
  if ($subDiv and $subDiv != "" and $subDiv != "None") then
    'xmldb:exist:///db/apps/edirom-content/' || $volSlug || '/sources/'
  else
    'xmldb:exist:///db/apps/edirom-content/' || $volSlug || '/sources/'

let $concCollection := if ($concPath and $concPath != '') then
  collection($concPath)[matches(document-uri(.), '\.xml$')]
else
  ()

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
        <name xml:lang='de'>Abschnitt</name>
        <name xml:lang='en'>Section</name>
      </names>
      {
        for $concId in tokenize($concIds, ',')[string-length(normalize-space(.)) > 0]
          let $concordance := (
            for $doc in $concCollection
            let $root := $doc/*[1]
            where $root/@xml:id = $concId
            return $root
          )[1]
        return
          if ($concordance) then
          <group>
              <names>
                <name xml:lang='de'>{$concordance/*[local-name() = 'labels'][@xml:lang='de']}</name>
                <name xml:lang='en'>{$concordance/*[local-name() = 'labels'][@xml:lang='en']}</name>
              </names>
              <connections label="Takt">
                <labels>
                  <label xml:lang="de">Takt</label>
                  <label xml:lang="en">Measure</label>
                </labels>
                {
                  for $connection in $concordance//$concordance/*[local-name() = 'connection']
                  return
                    <connection
                        xmlns="http://www.edirom.de/ns/1.3"
                        name="{$connection/@n}"
                        plist="{
                            for $source in $connection//*[local-name() = 'source']
                            return
                              if ($source[child::*[local-name() = 'part']]) then (
                                for $part in $source//*[local-name() = 'part']
                                return
                                  $part//*[local-name() = 'measure']/@target
                              ) else(
                                $source//*[local-name() = 'measure']/@target
                              )
                                
                        }"
                    />
                }
              </connections>
            </group>
          else
            ()
      }
    </groups>
  </concordance>